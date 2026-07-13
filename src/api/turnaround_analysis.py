"""
turnaround_analysis.py - Phase 5 Slice 1: Turnaround Violation Engine
GET /productions/{id}/crew/turnaround-analysis

Checks rest periods between consecutive shoot days against the
10-hour union-standard minimum turnaround. Wrap times earlier than
the call time are interpreted as after midnight (next calendar day).
Fires per-violation turnaround_violation signals (same dedupe and
auto-resolve pattern as the OT engine) and estimates forced-call
cost exposure for each violation.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Crew Intelligence"])

# Union-standard minimum rest between wrap and next call (hours)
_MIN_TURNAROUND_HOURS = 10.0
# Standard shoot day length used to derive hourly rates
_STANDARD_HOURS = 10.0


def _parse_clock(value: str):
    """Parse a '07:00 AM' style clock string. Returns None if unparseable."""
    if not value:
        return None
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt).time()
        except ValueError:
            continue
    return None


def _parse_date(value: str):
    """Parse a 'YYYY-MM-DD' date string. Returns None if unparseable."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


class TurnaroundPair(BaseModel):
    from_day: int
    to_day: int
    wrap: Optional[str]
    call: Optional[str]
    turnaround_hours: Optional[float]
    violation: bool
    hours_short: float
    forced_call_cost: float
    skipped_reason: Optional[str] = None


class TurnaroundResponse(BaseModel):
    production_id: str
    production_title: str
    min_turnaround_hours: float
    total_pairs: int
    pairs_analyzed: int
    pairs_skipped: int
    violations: int
    crew_count: int
    avg_daily_rate: float
    total_forced_call_exposure: float
    signals_created: int
    signals_resolved: int
    pairs: List[TurnaroundPair]


@router.get(
    "/productions/{production_id}/crew/turnaround-analysis",
    response_model=TurnaroundResponse,
    summary="Detect turnaround (rest period) violations between shoot days",
)
async def analyze_turnaround(production_id: str):
    """
    Walks consecutive shoot-day pairs, computes wrap-to-call rest hours,
    flags pairs under the 10-hour minimum, fires per-violation signals
    on the day whose call time invades the rest period, and estimates
    forced-call exposure (full crew day rate per violation).
    """
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id},
        order={"dayNumber": "asc"},
    )

    # Crew rates (same approach as OT engine)
    crew = await prisma.crewmember.find_many(
        where={"productionId": production_id, "status": "active"},
    )
    rates = [c.dailyRate for c in crew if c.dailyRate and c.dailyRate > 0]
    if not rates:
        rates = [c.weeklyRate / 5 for c in crew if c.weeklyRate and c.weeklyRate > 0]
    avg_daily_rate = sum(rates) / len(rates) if rates else 500.0
    crew_count = len(crew) if crew else 20

    # Existing unresolved turnaround signals, keyed by entityId (the invaded day)
    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "turnaround_violation",
            "source": "crew_engine",
            "resolved": False,
        }
    )
    existing_by_day = {sig.entityId: sig for sig in existing_signals}

    pairs: List[TurnaroundPair] = []
    violations = 0
    total_exposure = 0.0
    signals_created = 0
    signals_resolved = 0
    violating_day_ids = set()

    for i in range(len(shoot_days) - 1):
        d_from = shoot_days[i]
        d_to = shoot_days[i + 1]

        wrap_t = _parse_clock(d_from.wrapTime) if d_from.wrapTime else None
        call_t = _parse_clock(d_to.callTime) if d_to.callTime else None
        date_from = _parse_date(d_from.date) if d_from.date else None
        date_to = _parse_date(d_to.date) if d_to.date else None
        call_ref = _parse_clock(d_from.callTime) if d_from.callTime else None

        skipped = None
        if not d_from.wrapTime or not d_to.callTime:
            skipped = "missing wrap or call time"
        elif wrap_t is None or call_t is None:
            skipped = "unparseable wrap or call time"
        elif date_from is None or date_to is None:
            skipped = "missing or unparseable date"

        if skipped:
            pairs.append(TurnaroundPair(
                from_day=d_from.dayNumber, to_day=d_to.dayNumber,
                wrap=d_from.wrapTime, call=d_to.callTime,
                turnaround_hours=None, violation=False,
                hours_short=0.0, forced_call_cost=0.0,
                skipped_reason=skipped,
            ))
            continue

        # Build wrap datetime; wrap earlier than that day's call means
        # the crew wrapped after midnight (next calendar day).
        wrap_dt = datetime.combine(date_from, wrap_t)
        if call_ref is not None and wrap_t < call_ref:
            wrap_dt += timedelta(days=1)

        call_dt = datetime.combine(date_to, call_t)

        turnaround = (call_dt - wrap_dt).total_seconds() / 3600.0
        is_violation = turnaround < _MIN_TURNAROUND_HOURS
        hours_short = max(0.0, _MIN_TURNAROUND_HOURS - turnaround)

        # Forced-call exposure: full crew day rate for the invaded day.
        forced_cost = crew_count * avg_daily_rate if is_violation else 0.0

        if is_violation:
            violations += 1
            total_exposure += forced_cost
            violating_day_ids.add(d_to.id)

            message = (
                f"Turnaround violation: Day {d_from.dayNumber} wraps {d_from.wrapTime} "
                f"({d_from.date}) and Day {d_to.dayNumber} calls {d_to.callTime} "
                f"({d_to.date}) - only {turnaround:.1f} hours of rest against the "
                f"{_MIN_TURNAROUND_HOURS:.0f}-hour minimum ({hours_short:.1f} hours short). "
                f"Estimated forced-call exposure: ${forced_cost:,.0f} "
                f"({crew_count} crew at ${avg_daily_rate:,.0f}/day)."
            )
            if d_to.id in existing_by_day:
                await prisma.productionsignal.update(
                    where={"id": existing_by_day[d_to.id].id},
                    data={"severity": "high", "message": message},
                )
            else:
                await prisma.productionsignal.create(
                    data={
                        "productionId": production_id,
                        "signalType":   "turnaround_violation",
                        "severity":     "high",
                        "source":       "crew_engine",
                        "entityType":   "shoot_day",
                        "entityId":     d_to.id,
                        "message":      message,
                    }
                )
                signals_created += 1

        pairs.append(TurnaroundPair(
            from_day=d_from.dayNumber, to_day=d_to.dayNumber,
            wrap=d_from.wrapTime, call=d_to.callTime,
            turnaround_hours=round(turnaround, 2),
            violation=is_violation,
            hours_short=round(hours_short, 2),
            forced_call_cost=round(forced_cost, 2),
        ))

    # Auto-resolve signals for days no longer violating
    for day_id, sig in existing_by_day.items():
        if day_id not in violating_day_ids:
            await prisma.productionsignal.update(
                where={"id": sig.id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "crew_engine",
                },
            )
            signals_resolved += 1

    analyzed = sum(1 for p in pairs if p.skipped_reason is None)
    return TurnaroundResponse(
        production_id=production_id,
        production_title=production.title,
        min_turnaround_hours=_MIN_TURNAROUND_HOURS,
        total_pairs=len(pairs),
        pairs_analyzed=analyzed,
        pairs_skipped=len(pairs) - analyzed,
        violations=violations,
        crew_count=crew_count,
        avg_daily_rate=round(avg_daily_rate, 2),
        total_forced_call_exposure=round(total_exposure, 2),
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        pairs=pairs,
    )
