"""
burn_rate.py — Phase 4 Slice 2: Burn Rate Forecasting
GET /productions/{id}/budget/burn-rate

Calculates actual daily spend velocity from expense dates,
projects final cost to production completion, and fires a
budget_drift signal if the projection exceeds the budget.
"""
import logging
from datetime import date, datetime, timezone
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Budget Risk"])

# Industry-standard fallback durations (days) when endDate is not set
_DEFAULT_DURATION: Dict[str, int] = {
    "feature_film":  90,
    "feature":       90,
    "tv_series":     120,
    "documentary":   60,
    "commercial":    30,
}

class CategoryBurn(BaseModel):
    category: str
    total_spent: float
    daily_burn: float
    projected_total: float

class BurnRateResponse(BaseModel):
    production_id: str
    production_title: str
    budget_total: float
    total_spent: float
    days_elapsed: int
    days_remaining: Optional[int]
    total_duration_days: int
    daily_burn_rate: float
    projected_final_cost: float
    projected_variance: float
    projected_variance_pct: float
    on_track: bool
    forecast_basis: str   # "actual_dates" | "planned_dates" | "default_duration"
    signal_created: bool
    categories: List[CategoryBurn]


def _parse_date(dt) -> Optional[date]:
    if dt is None:
        return None
    if isinstance(dt, (date, datetime)):
        return dt.date() if isinstance(dt, datetime) else dt
    s = str(dt)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


@router.get(
    "/productions/{production_id}/budget/burn-rate",
    response_model=BurnRateResponse,
    summary="Calculate burn rate and project final production cost",
)
async def get_burn_rate(production_id: str):
    """
    Calculates actual daily spend velocity from dated expenses,
    projects to production end, and fires a budget_drift signal
    if the projection exceeds the total budget by more than 10%.
    Handles pre-production, active, and post productions gracefully.
    """
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    budget_total = production.budgetTotal or 0.0
    if budget_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Production has no budget set")

    # Load all expenses with dates
    expenses = await prisma.expense.find_many(
        where={"productionId": production_id},
        order={"expenseDate": "asc"},
    )

    total_spent = sum(e.amount for e in expenses)

    today = date.today()
    start_date = _parse_date(production.startDate)
    end_date = _parse_date(production.endDate)

    # Determine forecast basis and duration
    forecast_basis = "default_duration"
    if start_date and end_date:
        total_duration_days = (end_date - start_date).days
        forecast_basis = "planned_dates"
    elif start_date:
        prod_type = production.productionType or "feature"
        default_days = _DEFAULT_DURATION.get(prod_type, 90)
        end_date = start_date + __import__('datetime').timedelta(days=default_days)
        total_duration_days = default_days
        forecast_basis = "default_duration"
    else:
        # No start date — use today as start, default duration
        start_date = today
        prod_type = production.productionType or "feature"
        default_days = _DEFAULT_DURATION.get(prod_type, 90)
        end_date = start_date + __import__('datetime').timedelta(days=default_days)
        total_duration_days = default_days
        forecast_basis = "default_duration"

    # Days elapsed since start (floor at 1 to avoid division by zero)
    days_elapsed = max(1, (today - start_date).days)
    days_remaining = max(0, (end_date - today).days)

    # If we have expenses with dates, use the earliest expense date as burn start
    if expenses:
        earliest_expense = _parse_date(expenses[0].expenseDate)
        if earliest_expense and earliest_expense < today:
            days_elapsed = max(1, (today - earliest_expense).days)
            forecast_basis = "actual_dates"

    # Daily burn rate and projection
    daily_burn_rate = total_spent / days_elapsed
    projected_final_cost = total_spent + (daily_burn_rate * days_remaining)
    projected_variance = projected_final_cost - budget_total
    projected_variance_pct = (projected_variance / budget_total * 100) if budget_total > 0 else 0.0
    on_track = projected_final_cost <= budget_total * 1.05  # within 5% = on track

    # Category breakdown
    cat_totals: Dict[str, float] = {}
    for exp in expenses:
        cat_totals[exp.category] = cat_totals.get(exp.category, 0.0) + exp.amount

    categories = []
    for cat, spent in sorted(cat_totals.items()):
        cat_daily = spent / days_elapsed
        cat_projected = spent + (cat_daily * days_remaining)
        categories.append(CategoryBurn(
            category=cat,
            total_spent=round(spent, 2),
            daily_burn=round(cat_daily, 2),
            projected_total=round(cat_projected, 2),
        ))

    # Fire signal if projection exceeds budget by more than 10%
    signal_created = False
    if projected_variance_pct > 10:
        severity = "critical" if projected_variance_pct > 25 else "high"
        message = (
            f"Burn rate analysis projects final cost of ${projected_final_cost:,.0f} "
            f"against a ${budget_total:,.0f} budget "
            f"({projected_variance_pct:.1f}% over). "
            f"Current daily burn: ${daily_burn_rate:,.0f}/day over {days_elapsed} days."
        )
        # Check for existing unresolved burn_rate signal
        existing = await prisma.productionsignal.find_many(
            where={
                "productionId": production_id,
                "signalType": "budget_drift",
                "source": "burn_rate_engine",
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
                    "signalType":   "budget_drift",
                    "severity":     severity,
                    "source":       "burn_rate_engine",
                    "entityType":   "production",
                    "entityId":     production_id,
                    "message":      message,
                }
            )
            signal_created = True
    else:
        # Resolve any existing burn rate signal if now on track
        existing = await prisma.productionsignal.find_many(
            where={
                "productionId": production_id,
                "signalType": "budget_drift",
                "source": "burn_rate_engine",
                "resolved": False,
            }
        )
        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "burn_rate_engine",
                }
            )

    return BurnRateResponse(
        production_id=production_id,
        production_title=production.title,
        budget_total=budget_total,
        total_spent=round(total_spent, 2),
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        total_duration_days=total_duration_days,
        daily_burn_rate=round(daily_burn_rate, 2),
        projected_final_cost=round(projected_final_cost, 2),
        projected_variance=round(projected_variance, 2),
        projected_variance_pct=round(projected_variance_pct, 1),
        on_track=on_track,
        forecast_basis=forecast_basis,
        signal_created=signal_created,
        categories=categories,
    )
