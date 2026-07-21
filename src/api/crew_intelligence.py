"""
crew_intelligence.py — Phase 5 Slice 1: Workplace Compliance Engine
POST /productions/{id}/crew/analyze

Analyzes the shoot schedule for labor rule violations:
- Turnaround violations (IATSE 10hr min, SAG 12hr min between wrap and next call)
- Forced calls (turnaround < 8hr = critical)
- Extended-day meal penalty risk (page count implies shoot day beyond 12hrs)

Fires crew_conflict signals. Idempotent — resolves stale signals on re-run.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Crew Intelligence"])

# Union turnaround minimums (hours between wrap and next call)
_TURNAROUND_MIN = {
    "IATSE":     10.0,
    "SAG-AFTRA": 12.0,
    "SAG":       12.0,
    "DGA":       11.0,
    "TEAMSTERS": 10.0,
}
_DEFAULT_TURNAROUND = 10.0   # non-union default
_FORCED_CALL_HOURS  = 8.0    # under this = forced call (critical)
_STANDARD_DAY_HOURS = 12.0   # assumed shoot day length
_STANDARD_PAGES     = 8.0    # pages achievable in a standard day
_HOURS_PER_EXTRA_PAGE = 1.0  # each page over standard adds ~1hr to the day


class DayCompliance(BaseModel):
    day_number: int
    date: Optional[str]
    call_time: Optional[str]
    estimated_wrap: Optional[str]
    estimated_day_hours: float
    turnaround_to_next: Optional[float]
    turnaround_required: float
    violations: List[str]


class CrewAnalysisResponse(BaseModel):
    production_id: str
    production_title: str
    crew_count: int
    strictest_union: str
    turnaround_minimum: float
    days_analyzed: int
    total_violations: int
    signals_created: int
    signals_resolved: int
    days: List[DayCompliance]


def _parse_call(date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
    """Combine 'YYYY-MM-DD' + '06:00 AM' into a datetime. None if either missing."""
    if not date_str or not time_str:
        return None
    try:
        return datetime.strptime(f"{date_str} {time_str.strip()}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        try:
            # 24-hour fallback e.g. "18:00"
            return datetime.strptime(f"{date_str} {time_str.strip()}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None


@router.post(
    "/productions/{production_id}/crew/analyze",
    response_model=CrewAnalysisResponse,
    summary="Analyze the shoot schedule for labor rule violations",
)
async def analyze_crew(production_id: str):
    """
    Walks consecutive shoot days, estimates wrap from call time plus
    page-driven day length, and checks turnaround against the strictest
    union represented on the crew. Fires crew_conflict signals.
    """
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    crew = await prisma.crewmember.find_many(
        where={"productionId": production_id, "status": "active"},
    )

    # Strictest turnaround among unions present on this crew
    turnaround_req = _DEFAULT_TURNAROUND
    strictest = "Non-union"
    for member in crew:
        u = (member.union or "").strip().upper()
        req = _TURNAROUND_MIN.get(u)
        if req and req > turnaround_req:
            turnaround_req = req
            strictest = member.union

    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id},
        order={"dayNumber": "asc"},
    )

    day_results: List[DayCompliance] = []
    violation_msgs: List[str] = []

    prev_wrap: Optional[datetime] = None
    prev_day_number: Optional[int] = None

    for day in shoot_days:
        pages = day.totalPages or 0.0
        day_hours = _STANDARD_DAY_HOURS + max(0.0, pages - _STANDARD_PAGES) * _HOURS_PER_EXTRA_PAGE
        call_dt = _parse_call(day.date, day.callTime)
        wrap_dt = call_dt + timedelta(hours=day_hours) if call_dt else None

        violations: List[str] = []
        turnaround_hours: Optional[float] = None

        if call_dt and prev_wrap:
            turnaround_hours = round((call_dt - prev_wrap).total_seconds() / 3600.0, 1)
            if turnaround_hours < _FORCED_CALL_HOURS:
                msg = (
                    f"FORCED CALL: Day {day.dayNumber} call is only {turnaround_hours}h after "
                    f"Day {prev_day_number} estimated wrap (minimum {turnaround_req}h for {strictest})."
                )
                violations.append(msg)
                violation_msgs.append(("critical", msg))
            elif turnaround_hours < turnaround_req:
                msg = (
                    f"Turnaround violation: Day {day.dayNumber} call is {turnaround_hours}h after "
                    f"Day {prev_day_number} estimated wrap — {strictest} requires {turnaround_req}h."
                )
                violations.append(msg)
                violation_msgs.append(("high", msg))

        if day_hours > _STANDARD_DAY_HOURS:
            msg = (
                f"Extended day risk: Day {day.dayNumber} has {pages} pages scheduled — estimated "
                f"{day_hours:.1f}h day. Second meal penalty likely; budget meal penalties or split the day."
            )
            violations.append(msg)
            violation_msgs.append(("medium", msg))

        day_results.append(DayCompliance(
            day_number=day.dayNumber,
            date=day.date,
            call_time=day.callTime,
            estimated_wrap=wrap_dt.strftime("%Y-%m-%d %I:%M %p") if wrap_dt else None,
            estimated_day_hours=round(day_hours, 1),
            turnaround_to_next=None,  # filled below for the *previous* entry
            turnaround_required=turnaround_req,
            violations=violations,
        ))

        # Record this day's turnaround on the previous entry for display clarity
        if turnaround_hours is not None and len(day_results) >= 2:
            day_results[-2].turnaround_to_next = turnaround_hours

        if wrap_dt:
            prev_wrap = wrap_dt
            prev_day_number = day.dayNumber

    # -- Signal management (idempotent, source=crew_engine) --------------------
    existing = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "crew_conflict",
            "source": "crew_engine",
            "resolved": False,
        }
    )

    signals_created = 0
    signals_resolved = 0

    if violation_msgs:
        worst = "critical" if any(s == "critical" for s, _ in violation_msgs) \
            else "high" if any(s == "high" for s, _ in violation_msgs) else "medium"
        combined = " | ".join(m for _, m in violation_msgs)
        if len(combined) > 900:
            combined = combined[:897] + "..."
        message = f"{len(violation_msgs)} labor compliance issue(s) detected: {combined}"

        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={"severity": worst, "message": message},
            )
        else:
            await prisma.productionsignal.create(
                data={
                    "productionId": production_id,
                    "signalType":   "crew_conflict",
                    "severity":     worst,
                    "source":       "crew_engine",
                    "entityType":   "production",
                    "entityId":     production_id,
                    "message":      message,
                }
            )
            signals_created = 1
    else:
        for sig in existing:
            await prisma.productionsignal.update(
                where={"id": sig.id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "crew_engine",
                },
            )
            signals_resolved += 1

    return CrewAnalysisResponse(
        production_id=production_id,
        production_title=production.title,
        crew_count=len(crew),
        strictest_union=strictest,
        turnaround_minimum=turnaround_req,
        days_analyzed=len(shoot_days),
        total_violations=len(violation_msgs),
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        days=day_results,
    )
