"""
what_if.py — Phase 4 Slice 4: What-If Modeling
POST /productions/{id}/budget/what-if

Models the financial impact of production changes before they happen.
Currently supports: add_shoot_days scenario.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Budget Risk"])

# Cost drivers per additional shoot day (as % of daily burn rate)
# These weights reflect typical below-the-line day costs
_DAY_COST_WEIGHTS = {
    "labor":          0.45,   # Crew labor dominates
    "equipment":      0.20,   # Camera, lighting, grip rental
    "locations":      0.15,   # Location fees, permits
    "catering":       0.08,   # Craft services, meals
    "travel":         0.07,   # Ground transport, hotels
    "other":          0.05,   # Miscellaneous
}

class WhatIfRequest(BaseModel):
    scenario: str           # "add_shoot_days" | future scenarios
    value: float            # Number of days to add (for add_shoot_days)
    notes: Optional[str] = None

class DayCostBreakdown(BaseModel):
    category: str
    cost_per_day: float
    total_additional_cost: float

class WhatIfResponse(BaseModel):
    production_id: str
    production_title: str
    scenario: str
    scenario_description: str
    # Current state
    current_budget: float
    current_spend: float
    current_daily_burn: float
    current_shoot_days: int
    # What-if projection
    additional_days: float
    cost_per_additional_day: float
    total_additional_cost: float
    projected_total_spend: float
    projected_variance: float
    projected_variance_pct: float
    # Tax credit impact
    current_qualifying_spend: float
    projected_qualifying_spend: float
    qualifying_spend_increase: float
    # Risk assessment
    within_budget: bool
    recommendation: str
    cost_breakdown: List[DayCostBreakdown]


@router.post(
    "/productions/{production_id}/budget/what-if",
    response_model=WhatIfResponse,
    summary="Model the financial impact of production changes",
)
async def what_if(production_id: str, body: WhatIfRequest):
    """
    Models the cost impact of hypothetical production changes.

    Scenario: add_shoot_days
    - Calculates cost per additional shoot day from actual burn rate
    - Projects impact on total spend, qualifying spend, and budget variance
    - Provides category-level cost breakdown
    - Gives a go/no-go recommendation based on remaining budget headroom
    """
    if body.scenario != "add_shoot_days":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario {body.scenario!r}. Supported: add_shoot_days"
        )

    if body.value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="value must be greater than 0"
        )

    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    budget_total = production.budgetTotal or 0.0

    # Load expenses
    expenses = await prisma.expense.find_many(where={"productionId": production_id})
    total_spend = sum(e.amount for e in expenses)
    qualifying_spend = sum(e.amount for e in expenses if e.isQualifying)

    # Load shoot days to get current count
    shoot_days = await prisma.shootday.find_many(where={"productionId": production_id})
    current_shoot_days = len(shoot_days)

    # Calculate daily burn rate from actual expenses
    # Use shoot days as the denominator — cost per shoot day
    if current_shoot_days > 0 and total_spend > 0:
        daily_burn = total_spend / current_shoot_days
    elif total_spend > 0:
        # No shoot days scheduled — use budget / standard duration
        from datetime import date as _date
        _DEFAULT = {"feature": 30, "feature_film": 30, "tv_series": 45, "documentary": 20}
        default_days = _DEFAULT.get(production.productionType or "feature", 30)
        daily_burn = budget_total / default_days
    else:
        # No expenses yet — estimate from budget and production type
        _DEFAULT = {"feature": 30, "feature_film": 30, "tv_series": 45, "documentary": 20}
        default_days = _DEFAULT.get(production.productionType or "feature", 30)
        daily_burn = budget_total / default_days

    additional_days = body.value
    cost_per_day = daily_burn

    # Total additional cost
    total_additional_cost = cost_per_day * additional_days

    # Project qualifying spend increase
    # Qualifying ratio from current expenses
    qualifying_ratio = (qualifying_spend / total_spend) if total_spend > 0 else 0.75
    additional_qualifying = total_additional_cost * qualifying_ratio

    projected_total_spend = total_spend + total_additional_cost
    projected_qualifying = qualifying_spend + additional_qualifying
    projected_variance = projected_total_spend - budget_total
    projected_variance_pct = (projected_variance / budget_total * 100) if budget_total > 0 else 0.0
    within_budget = projected_total_spend <= budget_total

    # Category breakdown
    breakdown = []
    for cat, weight in _DAY_COST_WEIGHTS.items():
        cost_per_day_cat = cost_per_day * weight
        breakdown.append(DayCostBreakdown(
            category=cat,
            cost_per_day=round(cost_per_day_cat, 2),
            total_additional_cost=round(cost_per_day_cat * additional_days, 2),
        ))

    # Recommendation
    remaining_budget = budget_total - total_spend
    headroom_pct = (remaining_budget / budget_total * 100) if budget_total > 0 else 0.0

    if within_budget and headroom_pct > 10:
        recommendation = (
            f"Adding {additional_days:.0f} shoot day(s) is feasible. "
            f"Projected cost of ${total_additional_cost:,.0f} keeps you within budget "
            f"with ${remaining_budget - total_additional_cost:,.0f} remaining headroom."
        )
    elif within_budget:
        recommendation = (
            f"Adding {additional_days:.0f} shoot day(s) is tight but feasible. "
            f"Projected cost of ${total_additional_cost:,.0f} leaves less than 10% budget headroom. "
            f"Consider deferring non-essential scenes."
        )
    else:
        recommendation = (
            f"Adding {additional_days:.0f} shoot day(s) exceeds budget by ${abs(projected_variance):,.0f}. "
            f"Consider schedule compression, location consolidation, or reduced crew size "
            f"to offset the ${total_additional_cost:,.0f} additional cost."
        )

    scenario_description = (
        f"What happens if we add {additional_days:.0f} shoot day(s) to {production.title}? "
        f"Current schedule: {current_shoot_days} days at ${daily_burn:,.0f}/day average."
    )

    return WhatIfResponse(
        production_id=production_id,
        production_title=production.title,
        scenario=body.scenario,
        scenario_description=scenario_description,
        current_budget=budget_total,
        current_spend=round(total_spend, 2),
        current_daily_burn=round(daily_burn, 2),
        current_shoot_days=current_shoot_days,
        additional_days=additional_days,
        cost_per_additional_day=round(cost_per_day, 2),
        total_additional_cost=round(total_additional_cost, 2),
        projected_total_spend=round(projected_total_spend, 2),
        projected_variance=round(projected_variance, 2),
        projected_variance_pct=round(projected_variance_pct, 1),
        current_qualifying_spend=round(qualifying_spend, 2),
        projected_qualifying_spend=round(projected_qualifying, 2),
        qualifying_spend_increase=round(additional_qualifying, 2),
        within_budget=within_budget,
        recommendation=recommendation,
        cost_breakdown=breakdown,
    )
