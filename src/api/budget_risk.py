"""
budget_risk.py — Phase 4 Budget Risk Analysis Engine
POST /productions/{id}/budget/analyze

Reads actual expenses by category, compares against template allocations,
and auto-creates budget_drift signals for any category exceeding thresholds.
Idempotent — re-running resolves stale signals and creates fresh ones.
"""
import logging
from typing import List, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Budget Risk"])

# Drift thresholds
# Category allocation percentages by production type
_ALLOC_PCT = {
    'feature_film': {'labor':0.465,'equipment':0.11,'locations':0.08,'travel':0.04,'catering':0.02,'post_production':0.10,'insurance':0.025,'legal':0.01,'other':0.02},
    'documentary':  {'labor':0.29,'equipment':0.13,'locations':0.06,'travel':0.08,'catering':0.015,'post_production':0.17,'insurance':0.03,'legal':0.015,'other':0.025},
    'tv_series':    {'labor':0.49,'equipment':0.10,'locations':0.07,'travel':0.04,'catering':0.02,'post_production':0.10,'insurance':0.025,'legal':0.01,'other':0.02},
}

_WARN_PCT  = 0.10   # 10% over allocation → high signal
_CRIT_PCT  = 0.25   # 25% over allocation → critical signal

class CategoryRisk(BaseModel):
    category: str
    allocated: float
    actual: float
    variance: float
    variance_pct: float
    severity: str   # "ok" | "high" | "critical"

class BudgetRiskResponse(BaseModel):
    production_id: str
    budget_total: float
    total_actual: float
    total_allocated: float
    signals_created: int
    signals_resolved: int
    categories: List[CategoryRisk]


def _build_allocation(production_type: str, budget_total: float) -> Dict[str, float]:
    key = production_type if production_type in _ALLOC_PCT else 'feature_film'
    pcts = _ALLOC_PCT[key]
    return {cat: pct * budget_total for cat, pct in pcts.items()}


@router.post(
    "/productions/{production_id}/budget/analyze",
    response_model=BudgetRiskResponse,
    summary="Run budget drift analysis and auto-generate signals",
)
async def analyze_budget(production_id: str):
    """
    Compares actual expenses against template allocations.
    - Creates budget_drift signals for categories over threshold.
    - Resolves existing budget_drift signals that are no longer triggered.
    - Safe to call repeatedly — fully idempotent.
    """
    from datetime import datetime

    # Load production
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    budget_total = production.budgetTotal or 0.0
    if budget_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Production has no budget set")

    # Load all expenses
    expenses = await prisma.expense.find_many(where={"productionId": production_id})

    # Aggregate actual spend by category
    actual_by_cat: Dict[str, float] = {}
    for exp in expenses:
        actual_by_cat[exp.category] = actual_by_cat.get(exp.category, 0.0) + exp.amount

    # Build template allocations
    allocation = _build_allocation(production.productionType, budget_total)

    # Load existing unresolved budget_drift signals
    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "budget_drift",
            "resolved": False,
        }
    )
    # Map entityId (category) → signal id for quick lookup
    existing_by_cat = {s.entityId: s.id for s in existing_signals if s.entityId}

    signals_created = 0
    signals_resolved = 0
    categories: List[CategoryRisk] = []

    all_cats = set(list(allocation.keys()) + list(actual_by_cat.keys()))

    for cat in sorted(all_cats):
        allocated = allocation.get(cat, 0.0)
        actual    = actual_by_cat.get(cat, 0.0)
        variance  = actual - allocated
        variance_pct = (variance / allocated * 100) if allocated > 0 else 0.0

        # Determine severity
        if allocated > 0 and actual > allocated * (1 + _CRIT_PCT):
            severity = "critical"
        elif allocated > 0 and actual > allocated * (1 + _WARN_PCT):
            severity = "high"
        else:
            severity = "ok"

        categories.append(CategoryRisk(
            category=cat,
            allocated=round(allocated, 2),
            actual=round(actual, 2),
            variance=round(variance, 2),
            variance_pct=round(variance_pct, 1),
            severity=severity,
        ))

        if severity in ("high", "critical"):
            overage_amt = variance
            overage_pct = variance_pct
            message = (
                f"{cat.replace('_', ' ').title()} is {overage_pct:.1f}% over budget allocation. "
                f"Allocated ${allocated:,.0f}, actual ${actual:,.0f} "
                f"(+${overage_amt:,.0f} overage)."
            )
            if cat in existing_by_cat:
                # Update existing signal message and severity
                await prisma.productionsignal.update(
                    where={"id": existing_by_cat[cat]},
                    data={"severity": severity, "message": message}
                )
            else:
                # Create new signal
                await prisma.productionsignal.create(
                    data={
                        "productionId": production_id,
                        "signalType":   "budget_drift",
                        "severity":     severity,
                        "source":       "budget_engine",
                        "entityType":   "category",
                        "entityId":     cat,
                        "message":      message,
                    }
                )
                signals_created += 1
        else:
            # Category is within budget — resolve any existing signal
            if cat in existing_by_cat:
                await prisma.productionsignal.update(
                    where={"id": existing_by_cat[cat]},
                    data={
                        "resolved":   True,
                        "resolvedAt": datetime.utcnow(),
                        "resolvedBy": "budget_engine",
                    }
                )
                signals_resolved += 1

    total_actual    = sum(actual_by_cat.values())
    total_allocated = sum(allocation.values())

    return BudgetRiskResponse(
        production_id=production_id,
        budget_total=budget_total,
        total_actual=round(total_actual, 2),
        total_allocated=round(total_allocated, 2),
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        categories=categories,
    )
