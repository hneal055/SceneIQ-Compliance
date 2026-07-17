"""
schedule_risk.py - Phase 6 Slice 4: Schedule Risk Scoring Engine
GET /productions/{id}/schedule/risk-scores

Heuristic slippage risk per shoot day, computed from data the platform
already holds: page load vs the 8-page standard, EXT and NIGHT ratios,
complexity flags in notes (stunt/vfx/crowd/water), cast size, company
moves, and turnaround pressure from the previous day's rest period.

Every day's score is written to the Prediction table as a FORECAST -
a falsifiable, gradeable claim (source=schedule_risk_engine). Re-runs
update the existing proposed forecast per day rather than flooding.
Days scoring high or critical fire the schedule_slip signal (standard
dedupe/auto-resolve lifecycle).
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma
from src.api.tier_config import pages_standard

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Production Brain"])

_STANDARD_PAGES = 8.0
_MIN_COMFORT_REST = 11.0  # hours; below this, add turnaround pressure

# Factor weights (documented in the Bible; sum of caps = 105, capped 100)
_W_PAGES = 40.0
_W_EXT = 15.0
_W_NIGHT = 15.0
_W_FLAG_EACH = 5.0
_W_FLAG_CAP = 15.0
_W_CAST_CAP = 10.0
_W_MOVES_EACH = 5.0
_W_MOVES_CAP = 15.0
_W_TURNAROUND = 10.0

_FLAG_KEYWORDS = ("stunt", "vfx", "sfx", "pyro", "crowd", "water", "underwater",
                  "animal", "fight", "crash", "battle")

_TIERS = [(80.0, "critical"), (60.0, "high"), (40.0, "moderate"), (0.0, "low")]


def _parse_clock(value):
    if not value:
        return None
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(str(value).strip(), fmt).time()
        except ValueError:
            continue
    return None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


class DayRisk(BaseModel):
    day_number: int
    date: Optional[str]
    total_pages: float
    score: float
    tier: str
    factors: dict
    predicted_pages_at_risk: float
    prediction_id: Optional[str]


class ScheduleRiskResponse(BaseModel):
    production_id: str
    production_title: str
    days_scored: int
    highest_risk_day: Optional[int]
    highest_score: float
    forecasts_created: int
    forecasts_updated: int
    signals_created: int
    signals_resolved: int
    days: List[DayRisk]


@router.get(
    "/productions/{production_id}/schedule/risk-scores",
    response_model=ScheduleRiskResponse,
    summary="Heuristic slippage risk per shoot day, logged as gradeable forecasts",
)
async def score_schedule(production_id: str):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")
    _std = pages_standard(production)

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

    # Existing proposed forecasts for upsert semantics
    existing_forecasts = await prisma.prediction.find_many(
        where={
            "productionId": production_id,
            "source": "schedule_risk_engine",
            "kind": "forecast",
            "status": "proposed",
        }
    )
    forecast_by_day = {p.entityId: p for p in existing_forecasts}

    # Existing unresolved schedule_slip signals
    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "schedule_slip",
            "source": "schedule_risk_engine",
            "resolved": False,
        }
    )
    signal_by_day = {sig.entityId: sig for sig in existing_signals}

    days_out: List[DayRisk] = []
    forecasts_created = 0
    forecasts_updated = 0
    signals_created = 0
    signals_resolved = 0
    flagged_ids = set()
    prev_day = None

    for day in shoot_days:
        day_scenes = scenes_by_day.get(day.id, [])
        total_pages = day.totalPages if (day.totalPages and day.totalPages > 0) else \
            sum(s.pageCount or 0 for s in day_scenes)

        ext_pages = sum((s.pageCount or 0) for s in day_scenes
                        if (getattr(s, "locationType", "") or "").upper().startswith("EXT"))
        night_pages = sum((s.pageCount or 0) for s in day_scenes
                          if any(w in ((getattr(s, "timeOfDay", "") or "").upper())
                                 for w in ("NIGHT", "DUSK", "EVENING")))
        ext_ratio = (ext_pages / total_pages) if total_pages > 0 else 0.0
        night_ratio = (night_pages / total_pages) if total_pages > 0 else 0.0

        # Complexity flags from day + scene notes
        texts = [day.notes or ""]
        texts += [(s.notes or "") for s in day_scenes]
        blob = " ".join(texts).lower()
        flags_found = sorted({kw for kw in _FLAG_KEYWORDS if kw in blob})

        # Cast size across the day's scenes
        cast_ids = set()
        for s in day_scenes:
            for cid in (s.castIds or []):
                cast_ids.add(cid)

        # Company moves: unique scene locations (defensive - field may be absent)
        locs = {(getattr(s, "location", "") or "").strip().lower()
                for s in day_scenes if (getattr(s, "location", "") or "").strip()}
        moves = max(0, len(locs) - 1)

        # Turnaround pressure from the previous day
        turnaround_pressure = False
        if prev_day is not None:
            wrap_t = _parse_clock(getattr(prev_day, "wrapTime", None))
            call_t = _parse_clock(day.callTime)
            d_prev = _parse_date(prev_day.date)
            d_this = _parse_date(day.date)
            prev_call = _parse_clock(prev_day.callTime)
            if wrap_t and call_t and d_prev and d_this:
                wrap_dt = datetime.combine(d_prev, wrap_t)
                if prev_call and wrap_t < prev_call:
                    wrap_dt = wrap_dt.replace(day=wrap_dt.day)  # keep date math simple
                    from datetime import timedelta as _td
                    wrap_dt += _td(days=1)
                call_dt = datetime.combine(d_this, call_t)
                rest = (call_dt - wrap_dt).total_seconds() / 3600.0
                turnaround_pressure = rest < _MIN_COMFORT_REST

        # --- Score ---
        f_pages = min((total_pages / _std) * _W_PAGES, _W_PAGES * 1.5)
        f_ext = ext_ratio * _W_EXT
        f_night = night_ratio * _W_NIGHT
        f_flags = min(len(flags_found) * _W_FLAG_EACH, _W_FLAG_CAP)
        f_cast = min((len(cast_ids) / 6.0) * _W_CAST_CAP, _W_CAST_CAP)
        f_moves = min(moves * _W_MOVES_EACH, _W_MOVES_CAP)
        f_turn = _W_TURNAROUND if turnaround_pressure else 0.0

        score = min(100.0, f_pages + f_ext + f_night + f_flags + f_cast + f_moves + f_turn)
        tier = next(t for threshold, t in _TIERS if score >= threshold)

        # Predicted slippage: pages at risk of not completing
        overload = max(0.0, total_pages - _std)
        pages_at_risk = round(overload + (score / 100.0) * 1.0, 2)

        factors = {
            "pages": round(f_pages, 1), "ext": round(f_ext, 1),
            "night": round(f_night, 1), "flags": round(f_flags, 1),
            "flags_found": flags_found,
            "cast": round(f_cast, 1), "cast_count": len(cast_ids),
            "moves": round(f_moves, 1), "turnaround": round(f_turn, 1),
        }

        # --- Forecast row (upsert into Prediction table) ---
        payload = {
            "forecast": "schedule_slippage_risk",
            "day_number": day.dayNumber,
            "date": day.date,
            "score": round(score, 1),
            "tier": tier,
            "factors": factors,
            "predicted_pages_at_risk": pages_at_risk,
            "gradeable_claim": (
                f"Day {day.dayNumber} will complete its scheduled pages"
                if tier in ("low", "moderate") else
                f"Day {day.dayNumber} will fail to complete ~{pages_at_risk} scheduled pages"
            ),
        }
        narrative = (
            f"Day {day.dayNumber} slippage risk {score:.0f}/100 ({tier}). "
            f"Drivers: {total_pages:.2f} pages"
            + (f", {ext_ratio*100:.0f}% EXT" if ext_ratio > 0.3 else "")
            + (f", {night_ratio*100:.0f}% night" if night_ratio > 0.2 else "")
            + (f", flags: {', '.join(flags_found)}" if flags_found else "")
            + (f", {len(cast_ids)} cast" if len(cast_ids) >= 4 else "")
            + (", short turnaround before call" if turnaround_pressure else "")
            + f". Predicted pages at risk: {pages_at_risk}."
        )
        pred_id = None
        if day.id in forecast_by_day:
            row = await prisma.prediction.update(
                where={"id": forecast_by_day[day.id].id},
                data={"payload": json.dumps(payload), "narrative": narrative},
            )
            pred_id = row.id
            forecasts_updated += 1
        else:
            row = await prisma.prediction.create(data={
                "productionId": production_id,
                "source": "schedule_risk_engine",
                "kind": "forecast",
                "entityType": "shoot_day",
                "entityId": day.id,
                "payload": json.dumps(payload),
                "narrative": narrative,
            })
            pred_id = row.id
            forecasts_created += 1

        # --- schedule_slip signal for high/critical days ---
        if tier in ("high", "critical"):
            flagged_ids.add(day.id)
            severity = "high" if tier == "critical" else "medium"
            day_label = f"Day {day.dayNumber}" + (f" ({day.date})" if day.date else "")
            message = (
                f"Schedule slip risk: {day_label} scores {score:.0f}/100 ({tier}). "
                + narrative.split(". ", 1)[1]
            )
            if day.id in signal_by_day:
                await prisma.productionsignal.update(
                    where={"id": signal_by_day[day.id].id},
                    data={"severity": severity, "message": message},
                )
            else:
                await prisma.productionsignal.create(data={
                    "productionId": production_id,
                    "signalType":   "schedule_slip",
                    "severity":     severity,
                    "source":       "schedule_risk_engine",
                    "entityType":   "shoot_day",
                    "entityId":     day.id,
                    "message":      message,
                })
                signals_created += 1

        days_out.append(DayRisk(
            day_number=day.dayNumber, date=day.date,
            total_pages=round(total_pages, 2),
            score=round(score, 1), tier=tier,
            factors=factors,
            predicted_pages_at_risk=pages_at_risk,
            prediction_id=pred_id,
        ))
        prev_day = day

    # Auto-resolve signals for days no longer high/critical
    for day_id, sig in signal_by_day.items():
        if day_id not in flagged_ids:
            await prisma.productionsignal.update(
                where={"id": sig.id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "schedule_risk_engine",
                },
            )
            signals_resolved += 1

    highest = max(days_out, key=lambda d: d.score) if days_out else None
    return ScheduleRiskResponse(
        production_id=production_id,
        production_title=production.title,
        days_scored=len(days_out),
        highest_risk_day=highest.day_number if highest else None,
        highest_score=highest.score if highest else 0.0,
        forecasts_created=forecasts_created,
        forecasts_updated=forecasts_updated,
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        days=days_out,
    )
