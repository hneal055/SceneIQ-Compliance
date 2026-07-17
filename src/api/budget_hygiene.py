"""
budget_hygiene.py - VPS-2: Budget Hygiene Checks
GET /productions/{id}/budget/fringe-check

The single most common defect on indie and vertical-market budgets:
labor is budgeted, fringes are not. Payroll taxes and workers' comp
alone run ~16.5% on non-union labor (~31.5% union with health and
pension), so a budget with a $40K labor load and a $0 fringes line is
understating real cost by $5-6K - routinely 10%+ of a micro-budget
show.

This engine computes the expected fringe burden from the production's
actual crew roster (via the fringe engine), scans the production's
expense lines for anything that looks like a fringe/payroll-burden
line item, and fires a missing_fringes signal when labor exists but
no fringe line does. Standard dedupe/auto-resolve lifecycle.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma
from src.api.fringe_analysis import analyze_fringes

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Budget Risk"])

# Keywords that indicate a fringe/burden line item exists in the budget
_FRINGE_KEYWORDS = (
    "fringe", "payroll tax", "payroll taxes", "workers comp",
    "workers' comp", "workmen", "p&h", "pension", "health",
    "fica", "futa", "suta", "burden",
)


class FringeCheckResponse(BaseModel):
    production_id: str
    production_title: str
    budget_total: float
    crew_count: int
    base_labor_total: float
    expected_fringe_total: float
    blended_fringe_pct: float
    expense_lines_scanned: int
    fringe_lines_found: List[str]
    fringes_budgeted: bool
    verdict: str
    signal_created: bool
    signal_resolved: bool


def _looks_like_fringe(texts: List[str]) -> Optional[str]:
    blob = " ".join(t for t in texts if t).lower()
    for kw in _FRINGE_KEYWORDS:
        if kw in blob:
            return kw
    return None


@router.get(
    "/productions/{production_id}/budget/fringe-check",
    response_model=FringeCheckResponse,
    summary="Detect labor budgeted without fringes - the classic hidden exposure",
)
async def check_fringes(production_id: str):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    # Expected burden from the actual roster (the fringe engine dedupes
    # its own informational signal; safe to call)
    try:
        fr = await analyze_fringes(production_id)
        base_labor = fr.base_labor_daily * fr.shoot_day_count \
            if hasattr(fr, "shoot_day_count") else 0.0
        # Fall back to fields we know exist from the response model
        expected_total = getattr(fr, "fringe_burden_total", 0.0)
        blended_pct = getattr(fr, "blended_fringe_pct", 0.0)
        crew_count = getattr(fr, "crew_count", 0)
        base_labor_total = getattr(fr, "base_labor_total",
                                   getattr(fr, "base_labor_daily", 0.0))
    except HTTPException:
        # No crew seeded: nothing to check
        expected_total = 0.0
        blended_pct = 0.0
        crew_count = 0
        base_labor_total = 0.0

    # Scan expense lines for fringe-ish items (defensive across schema
    # variations: scan every string field on each expense row)
    fringe_lines: List[str] = []
    scanned = 0
    try:
        expenses = await prisma.expense.find_many(
            where={"productionId": production_id}
        )
        scanned = len(expenses)
        for e in expenses:
            try:
                values = [str(v) for v in e.dict().values()
                          if isinstance(v, str)]
            except Exception:
                values = []
            hit = _looks_like_fringe(values)
            if hit:
                label = getattr(e, "category", None) or \
                    getattr(e, "description", None) or hit
                fringe_lines.append(str(label))
    except Exception as exc:
        logger.warning("Expense scan unavailable: %s", exc)

    fringes_budgeted = len(fringe_lines) > 0
    labor_exists = crew_count > 0 and expected_total > 0

    # --- Signal lifecycle ---
    existing = await prisma.productionsignal.find_many(where={
        "productionId": production_id,
        "signalType": "missing_fringes",
        "source": "budget_hygiene",
        "resolved": False,
    })
    signal_created = False
    signal_resolved = False

    if labor_exists and not fringes_budgeted:
        verdict = (
            f"Labor is budgeted but fringes are not. Expected burden "
            f"~${expected_total:,.0f} ({blended_pct:.1f}% blended on "
            f"{crew_count} crew). This cost is real and will surface at "
            f"payroll whether or not it is on the budget."
        )
        message = (
            f"Missing fringes: {crew_count} crew are budgeted with no "
            f"fringe/payroll-burden line item found across {scanned} expense "
            f"lines. Expected fringe burden ~${expected_total:,.0f} "
            f"({blended_pct:.1f}% blended). Add a fringes line - payroll "
            f"taxes and workers' comp are owed regardless."
        )
        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={"severity": "medium", "message": message})
        else:
            await prisma.productionsignal.create(data={
                "productionId": production_id,
                "signalType":   "missing_fringes",
                "severity":     "medium",
                "source":       "budget_hygiene",
                "entityType":   "production",
                "entityId":     production_id,
                "message":      message,
            })
            signal_created = True
    else:
        if fringes_budgeted:
            verdict = (
                f"Fringes appear budgeted ({', '.join(sorted(set(fringe_lines))[:3])}). "
                f"Expected burden ~${expected_total:,.0f} - confirm the "
                f"budgeted amount covers it."
            )
        elif not labor_exists:
            verdict = "No crew roster seeded yet - nothing to check."
        else:
            verdict = "No fringe exposure detected."
        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={"resolved": True,
                      "resolvedAt": datetime.now(timezone.utc),
                      "resolvedBy": "budget_hygiene"})
            signal_resolved = True

    return FringeCheckResponse(
        production_id=production_id,
        production_title=production.title,
        budget_total=production.budgetTotal or 0.0,
        crew_count=crew_count,
        base_labor_total=round(base_labor_total, 2),
        expected_fringe_total=round(expected_total, 2),
        blended_fringe_pct=round(blended_pct, 2),
        expense_lines_scanned=scanned,
        fringe_lines_found=sorted(set(fringe_lines)),
        fringes_budgeted=fringes_budgeted,
        verdict=verdict,
        signal_created=signal_created,
        signal_resolved=signal_resolved,
    )
