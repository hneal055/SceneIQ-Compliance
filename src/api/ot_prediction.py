"""
ot_prediction.py — Phase 4 Slice 3: OT Prediction Engine
GET /productions/{id}/budget/ot-prediction

Analyzes shoot days against page count thresholds to predict
overtime risk and projected OT cost. Fires ot_spike signals
for days likely to run over standard 8-page day limit.
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
# OT premium multiplier (union standard: time-and-a-half)
_OT_MULTIPLIER = 0.5
# Signal threshold: projected OT > 5% of budget
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
    shoot_days: List[ShootDayRisk]


@router.get(
    "/productions/{production_id}/budget/ot-prediction",
    response_model=OTPredictionResponse,
    summary="Predict overtime risk from shoot day page counts",
)
async def predict_ot(production_id: str):
    """
    Analyzes all shoot days against the 8-page industry standard.
    Days with more than 8 pages are flagged as OT risk.
    Projects total OT cost using crew rates and fires an ot_spike
    signal if projected OT exceeds 5% of the total budget.
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

    # Analyze each shoot day
    day_risks: List[ShootDayRisk] = []
    total_projected_ot = 0.0
    total_pages = 0.0

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

        # Estimate OT hours: each page over standard = ~7.5 min of screen time
        # Industry rule: 1 page ≈ 1 hour of shoot time
        estimated_ot_hours = pages_over

        # OT cost: crew × avg_daily_rate × OT_premium × (OT_hours / standard_hours)
        standard_hours = 10.0  # standard 10-hour shoot day
        ot_cost = crew_count * avg_daily_rate * _OT_MULTIPLIER * (estimated_ot_hours / standard_hours)
        total_projected_ot += ot_cost

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

    # Fire ot_spike signal if OT projection exceeds threshold
    signal_created = False
    if projected_ot_pct > _OT_SIGNAL_PCT * 100:
        severity = "critical" if projected_ot_pct > 15 else "high" if projected_ot_pct > 8 else "medium"
        message = (
            f"{days_at_risk} of {len(shoot_days)} shoot days are over the 8-page standard. "
            f"Projected OT cost: ${total_projected_ot:,.0f} "
            f"({projected_ot_pct:.1f}% of budget). "
            f"Average {avg_pages:.1f} pages/day against {_STANDARD_PAGES:.0f}-page standard."
        )
        existing = await prisma.productionsignal.find_many(
            where={
                "productionId": production_id,
                "signalType": "ot_spike",
                "source": "ot_engine",
                "resolved": False,
            }
        )
        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={"severity": severity, "message": message}
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
        # Resolve existing OT signal if now under threshold
        existing = await prisma.productionsignal.find_many(
            where={
                "productionId": production_id,
                "signalType": "ot_spike",
                "source": "ot_engine",
                "resolved": False,
            }
        )
        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "ot_engine",
                }
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
        shoot_days=day_risks,
    )
