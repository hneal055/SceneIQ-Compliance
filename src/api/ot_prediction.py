"""
ot_prediction.py — Phase 4 Slice 3: OT Prediction Engine (v2)
GET /productions/{id}/budget/ot-prediction

Analyzes shoot days against the 8-page industry standard.
v2 changes:
  - Corrected OT cost model: OT hours are incremental hours paid at
    time-and-a-half (1.5x hourly), not a 0.5 premium on budgeted hours.
  - Per-day ot_spike signals (medium severity) for each HIGH risk day,
    with dedupe and auto-resolve.
  - Aggregate signal (OT > 5% of budget) unchanged.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Budget Risk"])

# Industry standard pages per shoot day
_STANDARD_PAGES = 8.0
# Standard shoot day length in hours (daily rate / this = hourly rate)
_STANDARD_HOURS = 10.0
# OT hours are paid at time-and-a-half
_OT_RATE_MULTIPLIER = 1.5
# Aggregate signal threshold: projected OT > 5% of budget
_OT_SIGNAL_PCT = 0.05


class ShootDayRisk(BaseModel):
    day_number: int
    date: Optional[str]
    total_pages: float
    pages_over: float
    ot_risk: str        # "none" | "low" | "high"
    estimated_ot_hours: float
    estimated_ot_cost: float


class OTPredictionResponse(BaseModel):
    production_id: str
    production_title: str
    budget_total: float
    total_shoot_days: int
    days_at_risk: int
    total_pages: float
    avg_pages_per_day: float
    avg_daily_rate: float
    crew_count: int
    projected_ot_cost: float
    projected_ot_pct: float
    signal_created: bool
    day_signals_created: int
    shoot_days: List[ShootDayRisk]


@router.get(
    "/productions/{production_id}/budget/ot-prediction",
    response_model=OTPredictionResponse,
    summary="Predict overtime risk from shoot day page counts",
)
async def predict_ot(production_id: str):
    """
    Analyzes all shoot days against the 8-page industry standard.
    Days over 8 pages are flagged as OT risk. Each HIGH risk day fires
    a per-day ot_spike signal (medium severity). If total projected OT
    exceeds 5% of budget, an aggregate production-level signal fires.
    """
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    budget_total = production.budgetTotal or 0.0

    # Load shoot days with their scenes
    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id},
        order={"dayNumber": "asc"},
    )

    # Load all scenes for this production keyed by shootDayId
    all_scenes = await prisma.scene.find_many(
        where={"productionId": production_id},
    )
    scenes_by_day: dict = {}
    for s in all_scenes:
        if s.shootDayId:
            scenes_by_day.setdefault(s.shootDayId, []).append(s)

    # Load crew members with rates
    crew = await prisma.crewmember.find_many(
        where={"productionId": production_id, "status": "active"},
    )

    # Calculate average daily rate across crew
    rates = [c.dailyRate for c in crew if c.dailyRate and c.dailyRate > 0]
    if not rates:
        # Fall back to weekly rate / 5 if no daily rates
        rates = [c.weeklyRate / 5 for c in crew if c.weeklyRate and c.weeklyRate > 0]
    avg_daily_rate = sum(rates) / len(rates) if rates else 500.0  # $500 default if no rates
    crew_count = len(crew) if crew else 20  # industry average crew size if no crew loaded

    # Derived hourly rate from standard day length
    avg_hourly_rate = avg_daily_rate / _STANDARD_HOURS

    # Load all unresolved OT signals for this production once,
    # split into per-day and aggregate for dedupe/resolve logic.
    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "ot_spike",
            "source": "ot_engine",
            "resolved": False,
        }
    )
    existing_day_signals = {
        sig.entityId: sig for sig in existing_signals if sig.entityType == "shoot_day"
    }
    existing_aggregate = [
        sig for sig in existing_signals if sig.entityType == "production"
    ]

    # Analyze each shoot day
    day_risks: List[ShootDayRisk] = []
    total_projected_ot = 0.0
    total_pages = 0.0
    day_signals_created = 0

    for day in shoot_days:
        # Use totalPages if set, otherwise sum scene page counts
        if day.totalPages and day.totalPages > 0:
            pages = day.totalPages
        elif day.id in scenes_by_day:
            pages = sum(s.pageCount or 0 for s in scenes_by_day[day.id])
        else:
            pages = 0.0

        total_pages += pages
        pages_over = max(0.0, pages - _STANDARD_PAGES)

        # OT risk classification
        if pages_over == 0:
            ot_risk = "none"
        elif pages_over <= 2:
            ot_risk = "low"
        else:
            ot_risk = "high"

        # Industry rule: 1 page over standard ~ 1 hour of additional shoot time
        estimated_ot_hours = pages_over

        # OT cost: incremental hours paid at time-and-a-half, whole crew
        ot_cost = crew_count * avg_hourly_rate * _OT_RATE_MULTIPLIER * estimated_ot_hours
        total_projected_ot += ot_cost

        # --- Per-day signal management ---
        if ot_risk == "high":
            day_label = f"Day {day.dayNumber}" + (f" ({day.date})" if day.date else "")
            day_message = (
                f"{day_label} is scheduled at {pages:.2f} pages "
                f"({pages_over:.2f} over the {_STANDARD_PAGES:.0f}-page standard). "
                f"Estimated {estimated_ot_hours:.1f} OT hours, "
                f"~${ot_cost:,.0f} projected OT cost."
            )
            if day.id in existing_day_signals:
                await prisma.productionsignal.update(
                    where={"id": existing_day_signals[day.id].id},
                    data={"severity": "medium", "message": day_message},
                )
            else:
                await prisma.productionsignal.create(
                    data={
                        "productionId": production_id,
                        "signalType":   "ot_spike",
                        "severity":     "medium",
                        "source":       "ot_engine",
                        "entityType":   "shoot_day",
                        "entityId":     day.id,
                        "message":      day_message,
                    }
                )
                day_signals_created += 1
        else:
            # Auto-resolve a per-day signal if this day is no longer high risk
            if day.id in existing_day_signals:
                await prisma.productionsignal.update(
                    where={"id": existing_day_signals[day.id].id},
                    data={
                        "resolved": True,
                        "resolvedAt": datetime.now(timezone.utc),
                        "resolvedBy": "ot_engine",
                    },
                )

        day_risks.append(ShootDayRisk(
            day_number=day.dayNumber,
            date=day.date,
            total_pages=round(pages, 2),
            pages_over=round(pages_over, 2),
            ot_risk=ot_risk,
            estimated_ot_hours=round(estimated_ot_hours, 1),
            estimated_ot_cost=round(ot_cost, 2),
        ))

    days_at_risk = sum(1 for d in day_risks if d.ot_risk != "none")
    avg_pages = total_pages / len(shoot_days) if shoot_days else 0.0
    projected_ot_pct = (total_projected_ot / budget_total * 100) if budget_total > 0 else 0.0

    # --- Aggregate signal: projected OT > 5% of budget ---
    signal_created = False
    if projected_ot_pct > _OT_SIGNAL_PCT * 100:
        severity = "critical" if projected_ot_pct > 15 else "high" if projected_ot_pct > 8 else "medium"
        message = (
            f"{days_at_risk} of {len(shoot_days)} shoot days are over the 8-page standard. "
            f"Projected OT cost: ${total_projected_ot:,.0f} "
            f"({projected_ot_pct:.1f}% of budget). "
            f"Average {avg_pages:.1f} pages/day against {_STANDARD_PAGES:.0f}-page standard."
        )
        if existing_aggregate:
            await prisma.productionsignal.update(
                where={"id": existing_aggregate[0].id},
                data={"severity": severity, "message": message},
            )
        else:
            await prisma.productionsignal.create(
                data={
                    "productionId": production_id,
                    "signalType":   "ot_spike",
                    "severity":     severity,
                    "source":       "ot_engine",
                    "entityType":   "production",
                    "entityId":     production_id,
                    "message":      message,
                }
            )
            signal_created = True
    else:
        # Resolve existing aggregate signal if now under threshold
        if existing_aggregate:
            await prisma.productionsignal.update(
                where={"id": existing_aggregate[0].id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "ot_engine",
                },
            )

    return OTPredictionResponse(
        production_id=production_id,
        production_title=production.title,
        budget_total=budget_total,
        total_shoot_days=len(shoot_days),
        days_at_risk=days_at_risk,
        total_pages=round(total_pages, 2),
        avg_pages_per_day=round(avg_pages, 2),
        avg_daily_rate=round(avg_daily_rate, 2),
        crew_count=crew_count,
        projected_ot_cost=round(total_projected_ot, 2),
        projected_ot_pct=round(projected_ot_pct, 1),
        signal_created=signal_created,
        day_signals_created=day_signals_created,
        shoot_days=day_risks,
    )
