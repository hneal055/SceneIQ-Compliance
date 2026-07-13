"""
meal_penalty.py - Phase 5 Slice 2: Meal Penalty Risk Engine
GET /productions/{id}/crew/meal-penalty-analysis

Derives meal-break requirements from each shoot day's call/wrap span.
Union-style rules (simplified): first meal within 6 hours of call;
second meal within 6 hours after first meal ends (~call + 12.5h with
a 30-minute meal). Days wrapping past the second-meal deadline are
flagged as meal penalty risk with estimated exposure. Fires per-day
meal_penalty signals using the standard dedupe/auto-resolve pattern.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Crew Intelligence"])

# First meal must start within this many hours of call
_FIRST_MEAL_HOURS = 6.0
# Meal duration (hours)
_MEAL_DURATION = 0.5
# Second meal must start within this many hours after first meal ends
_SECOND_MEAL_HOURS = 6.0
# Estimated penalty per crew member per half-hour increment past deadline
_PENALTY_PER_HALF_HOUR = 25.0


def _parse_clock(value: str):
    if not value:
        return None
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(value.strip(), fmt).time()
        except ValueError:
            continue
    return None


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


class MealRiskDay(BaseModel):
    day_number: int
    date: Optional[str]
    call: Optional[str]
    wrap: Optional[str]
    span_hours: Optional[float]
    meals_required: int
    second_meal_deadline_hours: float
    hours_past_deadline: float
    penalty_increments: int
    estimated_penalty: float
    risk: str  # "none" | "watch" | "penalty"
    skipped_reason: Optional[str] = None


class MealPenaltyResponse(BaseModel):
    production_id: str
    production_title: str
    crew_count: int
    penalty_per_half_hour: float
    days_analyzed: int
    days_skipped: int
    days_at_risk: int
    total_estimated_exposure: float
    signals_created: int
    signals_resolved: int
    days: List[MealRiskDay]


@router.get(
    "/productions/{production_id}/crew/meal-penalty-analysis",
    response_model=MealPenaltyResponse,
    summary="Detect meal penalty risk from shoot day call/wrap spans",
)
async def analyze_meal_penalties(production_id: str):
    """
    For each shoot day with call and wrap times, computes the working
    span and meal requirements. Days wrapping past the second-meal
    deadline (call + first meal window + meal + second meal window)
    are flagged with estimated penalty exposure and fire per-day
    meal_penalty signals.
    """
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id},
        order={"dayNumber": "asc"},
    )

    crew = await prisma.crewmember.find_many(
        where={"productionId": production_id, "status": "active"},
    )
    crew_count = len(crew) if crew else 20

    # Deadline (hours after call) for the second meal to start
    second_meal_deadline = _FIRST_MEAL_HOURS + _MEAL_DURATION + _SECOND_MEAL_HOURS

    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "meal_penalty",
            "source": "crew_engine",
            "resolved": False,
        }
    )
    existing_by_day = {sig.entityId: sig for sig in existing_signals}

    days_out: List[MealRiskDay] = []
    total_exposure = 0.0
    signals_created = 0
    signals_resolved = 0
    risk_day_ids = set()

    for day in shoot_days:
        call_t = _parse_clock(day.callTime) if day.callTime else None
        wrap_t = _parse_clock(day.wrapTime) if day.wrapTime else None
        date_d = _parse_date(day.date) if day.date else None

        skipped = None
        if not day.callTime or not day.wrapTime:
            skipped = "missing call or wrap time"
        elif call_t is None or wrap_t is None:
            skipped = "unparseable call or wrap time"

        if skipped:
            days_out.append(MealRiskDay(
                day_number=day.dayNumber, date=day.date,
                call=day.callTime, wrap=day.wrapTime,
                span_hours=None, meals_required=0,
                second_meal_deadline_hours=second_meal_deadline,
                hours_past_deadline=0.0, penalty_increments=0,
                estimated_penalty=0.0, risk="none",
                skipped_reason=skipped,
            ))
            continue

        # Span; wrap earlier than call means wrapped after midnight.
        ref_date = date_d or datetime(2000, 1, 1).date()
        call_dt = datetime.combine(ref_date, call_t)
        wrap_dt = datetime.combine(ref_date, wrap_t)
        if wrap_t < call_t:
            wrap_dt += timedelta(days=1)
        span = (wrap_dt - call_dt).total_seconds() / 3600.0

        meals_required = 0
        if span > _FIRST_MEAL_HOURS:
            meals_required = 1
        if span > second_meal_deadline:
            meals_required = 2

        hours_past = max(0.0, span - second_meal_deadline)
        increments = int(hours_past / 0.5)  # completed half-hours past deadline
        penalty = increments * _PENALTY_PER_HALF_HOUR * crew_count

        if hours_past > 0:
            risk = "penalty"
        elif span >= second_meal_deadline - 1.0:
            risk = "watch"  # within an hour of second-meal territory
        else:
            risk = "none"

        if risk == "penalty":
            total_exposure += penalty
            risk_day_ids.add(day.id)
            day_label = f"Day {day.dayNumber}" + (f" ({day.date})" if day.date else "")
            message = (
                f"Meal penalty risk: {day_label} spans {span:.1f} hours "
                f"(call {day.callTime}, wrap {day.wrapTime}). Second meal "
                f"deadline is {second_meal_deadline:.1f} hours after call; "
                f"this day runs {hours_past:.1f} hours past it "
                f"({increments} half-hour increments). Estimated exposure: "
                f"${penalty:,.0f} ({crew_count} crew at "
                f"${_PENALTY_PER_HALF_HOUR:,.0f}/half-hour)."
            )
            if day.id in existing_by_day:
                await prisma.productionsignal.update(
                    where={"id": existing_by_day[day.id].id},
                    data={"severity": "medium", "message": message},
                )
            else:
                await prisma.productionsignal.create(
                    data={
                        "productionId": production_id,
                        "signalType":   "meal_penalty",
                        "severity":     "medium",
                        "source":       "crew_engine",
                        "entityType":   "shoot_day",
                        "entityId":     day.id,
                        "message":      message,
                    }
                )
                signals_created += 1

        days_out.append(MealRiskDay(
            day_number=day.dayNumber, date=day.date,
            call=day.callTime, wrap=day.wrapTime,
            span_hours=round(span, 2), meals_required=meals_required,
            second_meal_deadline_hours=second_meal_deadline,
            hours_past_deadline=round(hours_past, 2),
            penalty_increments=increments,
            estimated_penalty=round(penalty, 2),
            risk=risk,
        ))

    # Auto-resolve signals for days no longer at penalty risk
    for day_id, sig in existing_by_day.items():
        if day_id not in risk_day_ids:
            await prisma.productionsignal.update(
                where={"id": sig.id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "crew_engine",
                },
            )
            signals_resolved += 1

    analyzed = sum(1 for d in days_out if d.skipped_reason is None)
    return MealPenaltyResponse(
        production_id=production_id,
        production_title=production.title,
        crew_count=crew_count,
        penalty_per_half_hour=_PENALTY_PER_HALF_HOUR,
        days_analyzed=analyzed,
        days_skipped=len(days_out) - analyzed,
        days_at_risk=len(risk_day_ids),
        total_estimated_exposure=round(total_exposure, 2),
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        days=days_out,
    )
