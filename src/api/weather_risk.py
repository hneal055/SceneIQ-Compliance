"""
weather_risk.py - Phase 6 Slice 3: Weather Risk Engine
GET /productions/{id}/schedule/weather-risk

Joins external weather forecasts (Open-Meteo, no API key required)
against the shoot schedule. For each shoot day with a date inside the
16-day forecast horizon: geocodes the day's location (falling back to
the production's jurisdiction), pulls the daily forecast, computes the
day's EXT page ratio from its scenes, and fires weather_risk signals
when an exterior-heavy day meets bad weather. Days beyond the horizon
are reported honestly as beyond_forecast_horizon rather than guessed.
Standard dedupe/auto-resolve signal lifecycle.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone, date, timedelta

import httpx

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Production Brain"])

# EXT page ratio above which a day is weather-exposed
_EXT_HEAVY_RATIO = 0.5
# Precipitation probability thresholds (%)
_PRECIP_MEDIUM = 50
_PRECIP_HIGH = 70
# Max daily wind gust considered disruptive (km/h)
_WIND_HIGH = 40.0
# Open-Meteo forecast horizon (days from today)
_FORECAST_HORIZON_DAYS = 16

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class DayWeather(BaseModel):
    day_number: int
    date: Optional[str]
    location_used: Optional[str]
    total_pages: float
    ext_pages: float
    ext_ratio: Optional[float]
    forecast_status: str  # ok | beyond_forecast_horizon | no_date | no_location | fetch_failed
    precip_probability: Optional[int] = None
    wind_max_kmh: Optional[float] = None
    temp_max_c: Optional[float] = None
    temp_min_c: Optional[float] = None
    risk: str = "none"  # none | watch | risk


class WeatherResponse(BaseModel):
    production_id: str
    production_title: str
    forecast_provider: str
    days_analyzed: int
    days_in_horizon: int
    ext_heavy_days: int
    risk_days: int
    signals_created: int
    signals_resolved: int
    days: List[DayWeather]


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


async def _geocode(client: httpx.AsyncClient, name: str, cache: dict):
    if not name:
        return None
    key = name.strip().lower()
    if key in cache:
        return cache[key]
    try:
        r = await client.get(_GEOCODE_URL, params={"name": name, "count": 1}, timeout=10)
        r.raise_for_status()
        results = r.json().get("results") or []
        coords = None
        if results:
            coords = (results[0]["latitude"], results[0]["longitude"], results[0].get("name", name))
        cache[key] = coords
        return coords
    except Exception as exc:
        logger.warning("Geocode failed for %r: %s", name, exc)
        cache[key] = None
        return None


async def _forecast(client: httpx.AsyncClient, lat: float, lon: float,
                    start: date, end: date, cache: dict):
    key = (round(lat, 3), round(lon, 3), start.isoformat(), end.isoformat())
    if key in cache:
        return cache[key]
    try:
        r = await client.get(_FORECAST_URL, params={
            "latitude": lat, "longitude": lon,
            "daily": "precipitation_probability_max,wind_speed_10m_max,"
                     "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }, timeout=10)
        r.raise_for_status()
        daily = r.json().get("daily", {})
        by_date = {}
        for i, d in enumerate(daily.get("time", [])):
            by_date[d] = {
                "precip": (daily.get("precipitation_probability_max") or [None] * 99)[i],
                "wind": (daily.get("wind_speed_10m_max") or [None] * 99)[i],
                "tmax": (daily.get("temperature_2m_max") or [None] * 99)[i],
                "tmin": (daily.get("temperature_2m_min") or [None] * 99)[i],
            }
        cache[key] = by_date
        return by_date
    except Exception as exc:
        logger.warning("Forecast fetch failed for (%s, %s): %s", lat, lon, exc)
        cache[key] = None
        return None


@router.get(
    "/productions/{production_id}/schedule/weather-risk",
    response_model=WeatherResponse,
    summary="Forecast-driven weather risk for exterior-heavy shoot days",
)
async def analyze_weather(production_id: str):
    production = await prisma.production.find_unique(
        where={"id": production_id}, include={"jurisdiction": True},
    )
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id}, order={"dayNumber": "asc"},
    )
    if not shoot_days:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No shoot days")

    scenes = await prisma.scene.find_many(where={"productionId": production_id})
    scenes_by_day: dict = {}
    for s in scenes:
        if s.shootDayId:
            scenes_by_day.setdefault(s.shootDayId, []).append(s)

    jurisdiction_name = production.jurisdiction.name if production.jurisdiction else None

    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "weather_risk",
            "source": "weather_engine",
            "resolved": False,
        }
    )
    existing_by_day = {sig.entityId: sig for sig in existing_signals}

    today = date.today()
    horizon_end = today + timedelta(days=_FORECAST_HORIZON_DAYS)

    days_out: List[DayWeather] = []
    geo_cache: dict = {}
    fc_cache: dict = {}
    signals_created = 0
    signals_resolved = 0
    risk_day_ids = set()
    in_horizon = 0
    ext_heavy = 0

    async with httpx.AsyncClient() as client:
        for day in shoot_days:
            day_scenes = scenes_by_day.get(day.id, [])
            total_pages = sum(s.pageCount or 0 for s in day_scenes)
            ext_pages = sum(
                (s.pageCount or 0) for s in day_scenes
                if (s.locationType or "").upper().startswith("EXT")
            )
            ext_ratio = (ext_pages / total_pages) if total_pages > 0 else None

            entry = DayWeather(
                day_number=day.dayNumber, date=day.date,
                location_used=None,
                total_pages=round(total_pages, 2),
                ext_pages=round(ext_pages, 2),
                ext_ratio=round(ext_ratio, 2) if ext_ratio is not None else None,
                forecast_status="no_date",
            )

            d = _parse_date(day.date)
            if d is None:
                days_out.append(entry)
                continue
            if not (today <= d <= horizon_end):
                entry.forecast_status = "beyond_forecast_horizon"
                days_out.append(entry)
                continue
            in_horizon += 1

            # Location: day-level first, jurisdiction fallback
            coords = await _geocode(client, day.location, geo_cache) if day.location else None
            if coords is None and jurisdiction_name:
                coords = await _geocode(client, jurisdiction_name, geo_cache)
            if coords is None:
                entry.forecast_status = "no_location"
                days_out.append(entry)
                continue
            lat, lon, resolved_name = coords
            entry.location_used = resolved_name

            fc = await _forecast(client, lat, lon, d, d, fc_cache)
            wx = fc.get(d.isoformat()) if fc else None
            if not wx:
                entry.forecast_status = "fetch_failed"
                days_out.append(entry)
                continue

            entry.forecast_status = "ok"
            entry.precip_probability = wx["precip"]
            entry.wind_max_kmh = wx["wind"]
            entry.temp_max_c = wx["tmax"]
            entry.temp_min_c = wx["tmin"]

            is_ext_heavy = ext_ratio is not None and ext_ratio > _EXT_HEAVY_RATIO
            if is_ext_heavy:
                ext_heavy += 1

            precip = wx["precip"] if wx["precip"] is not None else 0
            wind = wx["wind"] if wx["wind"] is not None else 0.0

            if is_ext_heavy and (precip >= _PRECIP_HIGH or wind >= _WIND_HIGH):
                entry.risk = "risk"
                severity = "high"
            elif is_ext_heavy and precip >= _PRECIP_MEDIUM:
                entry.risk = "risk"
                severity = "medium"
            elif is_ext_heavy and precip >= _PRECIP_MEDIUM - 20:
                entry.risk = "watch"
                severity = None
            else:
                severity = None

            if entry.risk == "risk":
                risk_day_ids.add(day.id)
                day_label = f"Day {day.dayNumber} ({day.date})"
                message = (
                    f"Weather risk: {day_label} is {ext_ratio*100:.0f}% exterior pages "
                    f"({ext_pages:.2f} of {total_pages:.2f}) at {resolved_name}, and the "
                    f"forecast shows {precip}% precipitation probability"
                    + (f" with wind to {wind:.0f} km/h" if wind >= _WIND_HIGH else "")
                    + ". Prepare a cover set or weather day, and confirm insurance "
                      "weather provisions."
                )
                if day.id in existing_by_day:
                    await prisma.productionsignal.update(
                        where={"id": existing_by_day[day.id].id},
                        data={"severity": severity, "message": message},
                    )
                else:
                    await prisma.productionsignal.create(
                        data={
                            "productionId": production_id,
                            "signalType":   "weather_risk",
                            "severity":     severity,
                            "source":       "weather_engine",
                            "entityType":   "shoot_day",
                            "entityId":     day.id,
                            "message":      message,
                        }
                    )
                    signals_created += 1

            days_out.append(entry)

    # Auto-resolve signals for days no longer at risk
    for day_id, sig in existing_by_day.items():
        if day_id not in risk_day_ids:
            await prisma.productionsignal.update(
                where={"id": sig.id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "weather_engine",
                },
            )
            signals_resolved += 1

    return WeatherResponse(
        production_id=production_id,
        production_title=production.title,
        forecast_provider="open-meteo.com",
        days_analyzed=len(days_out),
        days_in_horizon=in_horizon,
        ext_heavy_days=ext_heavy,
        risk_days=len(risk_day_ids),
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        days=days_out,
    )
