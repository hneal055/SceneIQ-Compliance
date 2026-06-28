"""
Largo / MMB Connector integration endpoint.
Accepts a project submission and returns incentive analysis.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])


class LargoProject(BaseModel):
    project_name: str
    genre: Optional[str] = "drama"
    budget: Optional[float] = 0
    locations: Optional[List[str]] = []
    audience_score: Optional[float] = None
    include_logo: Optional[bool] = False
    local_hire_pct: Optional[float] = 0.0
    diversity_score: Optional[float] = 0.0


@router.post("/largo/project", summary="Evaluate a project from Largo or MMB Connector")
async def evaluate_largo_project(project: LargoProject):
    location_terms = [loc.strip() for loc in (project.locations or []) if loc.strip()]

    # Collect unique jurisdictions matching any of the location terms
    seen_ids: set = set()
    jurisdictions = []
    for term in location_terms:
        matches = await prisma.jurisdiction.find_many(
            where={
                "OR": [
                    {"code": {"equals": term.upper()}},
                    {"name": {"contains": term}},
                ],
                "active": True,
            }
        )
        for j in matches:
            if j.id not in seen_ids:
                seen_ids.add(j.id)
                jurisdictions.append(j)

    if not jurisdictions:
        jurisdictions = await prisma.jurisdiction.find_many(
            where={"active": True}, order={"name": "asc"}, take=5
        )

    budget = project.budget or 0
    qualifying_spend = budget * 0.8

    recommendations = []
    total_credits = 0.0

    for j in jurisdictions:
        rules = await prisma.incentiverule.find_many(
            where={"jurisdictionId": j.id, "active": True},
            order={"percentage": "desc"},
        )
        if not rules:
            continue

        top_rule = rules[0]
        rate = (top_rule.percentage or 0) / 100
        min_spend = top_rule.minSpend or 0
        eligible = qualifying_spend >= min_spend if min_spend else True
        ineligibility_reason = None if eligible else f"Minimum qualifying spend of ${min_spend:,.0f} not met (current: ${qualifying_spend:,.0f})"

        base_credit = qualifying_spend * rate if eligible else 0.0
        if top_rule.maxCredit:
            base_credit = min(base_credit, top_rule.maxCredit)

        bonuses_applied = []
        bonus_amount = 0.0

        # Local hire bonus (5% if >= 15% local crew)
        if eligible and (project.local_hire_pct or 0) >= 0.15:
            bonus_rate = 0.05
            bonus = qualifying_spend * bonus_rate
            bonuses_applied.append({"name": "Local Hire Bonus", "rate": bonus_rate, "amount": round(bonus, 2)})
            bonus_amount += bonus

        # Georgia-specific: promotional logo bonus
        if eligible and project.include_logo and j.code == "GA":
            bonus_rate = 0.10
            bonus = qualifying_spend * bonus_rate
            bonuses_applied.append({"name": "Georgia Promotional Logo Bonus", "rate": bonus_rate, "amount": round(bonus, 2)})
            bonus_amount += bonus

        estimated_credit = round(base_credit + bonus_amount, 2)
        effective_rate = round((estimated_credit / budget) if budget else 0, 4)

        # Audit readiness score (simple heuristic)
        audit_score = 60
        if budget >= 1_000_000:
            audit_score += 15
        if (project.local_hire_pct or 0) >= 0.15:
            audit_score += 10
        if (project.diversity_score or 0) >= 0.20:
            audit_score += 10
        if project.include_logo:
            audit_score += 5
        audit_score = min(audit_score, 100)

        # Pre-application checklist from rule requirements
        checklist = [
            "File production registration with state film office",
            "Maintain detailed expense records by category",
            "Obtain certificate of good standing",
        ]
        if min_spend:
            checklist.insert(1, f"Meet minimum qualifying spend of ${min_spend:,.0f}")
        if j.code == "GA" and project.include_logo:
            checklist.append("Include Georgia promotional logo in end credits")
        else:
            reqs = top_rule.requirements or {}
            if isinstance(reqs, dict) and reqs.get("promotionalRequirements"):
                checklist.append("Include Georgia promotional logo in end credits")

        if eligible:
            total_credits += estimated_credit

        recommendations.append({
            "program_name": top_rule.ruleName,
            "jurisdiction": f"{j.name}, {j.country}",
            "eligible": eligible,
            "estimated_credit": estimated_credit,
            "credit_rate": effective_rate,
            "ineligibility_reason": ineligibility_reason,
            "qualified_spend": round(qualifying_spend, 2),
            "qualified_categories": top_rule.eligibleExpenses or [],
            "bonuses_applied": bonuses_applied,
            "audit_readiness_score": audit_score,
            "pre_application_checklist": checklist,
            "transferable": False,
            "sunset_date": top_rule.expirationDate.isoformat() if top_rule.expirationDate else None,
        })

    recommendations.sort(key=lambda r: r["estimated_credit"], reverse=True)

    return {
        "project_name": project.project_name,
        "genre": project.genre,
        "budget": budget,
        "audience_score": project.audience_score,
        "total_estimated_credits": round(total_credits, 2),
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "powered_by": "SceneIQ Rules Engine v1 â€” Scene Reader Studio Technologies LLC",
    }




