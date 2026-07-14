"""
fringe_analysis.py - Phase 5 Slice 3: Fringe Rate Engine
GET /productions/{id}/crew/fringe-analysis

Calculates fringe burden (payroll taxes, workers comp, union health
and pension, payroll handling) on crew labor. Produces per-member
loaded rates, department rollups, union/non-union split, and total
production fringe exposure across scheduled shoot days. Fires an
informational fringe_burden signal when the burden is material
relative to budget. Exposes get_fringe_multiplier() for other
engines (OT, turnaround) to price loaded rather than bare rates.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Crew Intelligence"])

# Fringe components (fractions of base labor)
_PAYROLL_TAXES = 0.11      # FICA / FUTA / SUTA
_WORKERS_COMP = 0.04
_UNION_HEALTH_PENSION = 0.15   # union crew only
_PAYROLL_HANDLING = 0.015

_NONUNION_FRINGE = _PAYROLL_TAXES + _WORKERS_COMP + _PAYROLL_HANDLING            # 0.165
_UNION_FRINGE = _NONUNION_FRINGE + _UNION_HEALTH_PENSION                          # 0.315

# Signal thresholds: fringe burden as % of total budget
_SIGNAL_LOW_PCT = 1.0
_SIGNAL_MEDIUM_PCT = 3.0


def get_fringe_multiplier(union: Optional[str]) -> float:
    """Loaded-rate multiplier for a crew member. Importable by other engines."""
    return 1.0 + (_UNION_FRINGE if union else _NONUNION_FRINGE)


class CrewFringe(BaseModel):
    name: str
    role: str
    department: str
    union: Optional[str]
    daily_rate: float
    fringe_rate_pct: float
    fringe_daily: float
    loaded_daily_rate: float


class DepartmentFringe(BaseModel):
    department: str
    headcount: int
    base_daily: float
    fringe_daily: float
    loaded_daily: float


class FringeResponse(BaseModel):
    production_id: str
    production_title: str
    budget_total: float
    crew_count: int
    union_count: int
    nonunion_count: int
    union_fringe_pct: float
    nonunion_fringe_pct: float
    base_labor_daily: float
    fringe_burden_daily: float
    loaded_labor_daily: float
    blended_fringe_pct: float
    scheduled_shoot_days: int
    fringe_burden_total: float
    loaded_labor_total: float
    fringe_pct_of_budget: float
    signal_created: bool
    departments: List[DepartmentFringe]
    crew: List[CrewFringe]


@router.get(
    "/productions/{production_id}/crew/fringe-analysis",
    response_model=FringeResponse,
    summary="Calculate fringe burden and loaded labor rates",
)
async def analyze_fringes(production_id: str):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    budget_total = production.budgetTotal or 0.0

    crew = await prisma.crewmember.find_many(
        where={"productionId": production_id, "status": "active"},
        order={"department": "asc"},
    )
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active crew members - seed crew before running fringe analysis",
        )

    shoot_days = await prisma.shootday.count(where={"productionId": production_id})

    crew_out: List[CrewFringe] = []
    dept_agg: dict = {}
    base_daily = 0.0
    fringe_daily = 0.0
    union_count = 0

    for c in crew:
        rate = c.dailyRate if (c.dailyRate and c.dailyRate > 0) else (
            (c.weeklyRate / 5) if (c.weeklyRate and c.weeklyRate > 0) else 0.0
        )
        frac = _UNION_FRINGE if c.union else _NONUNION_FRINGE
        if c.union:
            union_count += 1
        fringe = rate * frac
        base_daily += rate
        fringe_daily += fringe

        crew_out.append(CrewFringe(
            name=c.name, role=c.role, department=c.department, union=c.union,
            daily_rate=round(rate, 2),
            fringe_rate_pct=round(frac * 100, 1),
            fringe_daily=round(fringe, 2),
            loaded_daily_rate=round(rate + fringe, 2),
        ))

        d = dept_agg.setdefault(c.department, {"n": 0, "base": 0.0, "fringe": 0.0})
        d["n"] += 1
        d["base"] += rate
        d["fringe"] += fringe

    departments = [
        DepartmentFringe(
            department=k, headcount=v["n"],
            base_daily=round(v["base"], 2),
            fringe_daily=round(v["fringe"], 2),
            loaded_daily=round(v["base"] + v["fringe"], 2),
        )
        for k, v in sorted(dept_agg.items())
    ]

    blended_pct = (fringe_daily / base_daily * 100) if base_daily > 0 else 0.0
    fringe_total = fringe_daily * shoot_days
    loaded_total = (base_daily + fringe_daily) * shoot_days
    pct_of_budget = (fringe_total / budget_total * 100) if budget_total > 0 else 0.0

    # Informational signal when the fringe burden is material
    signal_created = False
    existing = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "fringe_burden",
            "source": "crew_engine",
            "resolved": False,
        }
    )
    if pct_of_budget > _SIGNAL_LOW_PCT:
        severity = "medium" if pct_of_budget > _SIGNAL_MEDIUM_PCT else "low"
        message = (
            f"Fringe burden on crew labor: ${fringe_daily:,.0f}/day "
            f"({blended_pct:.1f}% blended rate on ${base_daily:,.0f} base labor), "
            f"${fringe_total:,.0f} across {shoot_days} scheduled shoot days "
            f"({pct_of_budget:.1f}% of budget). Union crew: {union_count} at "
            f"{_UNION_FRINGE*100:.1f}%; non-union: {len(crew) - union_count} at "
            f"{_NONUNION_FRINGE*100:.1f}%. Confirm fringes are line-itemed in the budget."
        )
        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={"severity": severity, "message": message},
            )
        else:
            await prisma.productionsignal.create(
                data={
                    "productionId": production_id,
                    "signalType":   "fringe_burden",
                    "severity":     severity,
                    "source":       "crew_engine",
                    "entityType":   "production",
                    "entityId":     production_id,
                    "message":      message,
                }
            )
            signal_created = True
    else:
        if existing:
            await prisma.productionsignal.update(
                where={"id": existing[0].id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "crew_engine",
                },
            )

    return FringeResponse(
        production_id=production_id,
        production_title=production.title,
        budget_total=budget_total,
        crew_count=len(crew),
        union_count=union_count,
        nonunion_count=len(crew) - union_count,
        union_fringe_pct=round(_UNION_FRINGE * 100, 1),
        nonunion_fringe_pct=round(_NONUNION_FRINGE * 100, 1),
        base_labor_daily=round(base_daily, 2),
        fringe_burden_daily=round(fringe_daily, 2),
        loaded_labor_daily=round(base_daily + fringe_daily, 2),
        blended_fringe_pct=round(blended_pct, 1),
        scheduled_shoot_days=shoot_days,
        fringe_burden_total=round(fringe_total, 2),
        loaded_labor_total=round(loaded_total, 2),
        fringe_pct_of_budget=round(pct_of_budget, 2),
        signal_created=signal_created,
        departments=departments,
        crew=crew_out,
    )
