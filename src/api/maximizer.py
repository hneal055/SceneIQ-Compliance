"""
/maximize  â€”  SceneIQ Incentive Maximizer API
=================================================
Resolves jurisdiction layers from a lat/lng or explicit codes,
applies the local_rules stacking engine, and returns a fully-broken-
down incentive package.

Routes
------
POST /maximize                        Full maximize (lat/lng or codes + spend)
GET  /maximize/lookup                 Resolve which jurisdictions a point falls in
GET  /maximize/maximum-possible-credit  Best-case incentive summary card data
"""

from datetime import datetime, timezone
from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from maximizer import SceneIQMaximizer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/maximize", tags=["Maximizer"])

_engine = None


def _get_engine() -> SceneIQMaximizer:
    global _engine
    if _engine is None:
        _engine = SceneIQMaximizer()
    return _engine


# -- Request / Response models -------------------------------------------------

class MaximizeRequest(BaseModel):
    lat: Optional[float] = Field(None, description="Latitude (WGS-84)")
    lng: Optional[float] = Field(None, description="Longitude (WGS-84)")
    jurisdiction_codes: Optional[List[str]] = Field(
        None, description="Explicit jurisdiction codes (overrides lat/lng)"
    )
    project_type: str = Field("all", description="Project type filter (e.g. 'film', 'solar')")
    qualified_spend: Optional[float] = Field(
        None, description="Qualified production spend in USD - enables real dollar calculation"
    )
    spend_by_location: Optional[dict] = Field(
        None,
        description=(
            "Per-jurisdiction qualifying spend (CODE -> USD). "
            "Rules for a jurisdiction use its entry instead of qualified_spend. "
            "Useful for split-location shoots where a city/county bonus "
            "should only apply to local spend. "
            "Example: {'IL': 5000000, 'IL-COOK': 2000000}"
        ),
    )


class RuleDetail(BaseModel):
    jurisdiction_name: str
    rule_key: str
    rule_type: str
    raw_value: float
    value_unit: str
    computed_value: float


class MaximizeResponse(BaseModel):
    resolved_state: Optional[str]
    jurisdictions_evaluated: int
    qualified_spend: Optional[float]
    total_incentive_usd: float
    effective_rate: Optional[float]
    breakdown: dict
    applied_rules: List[RuleDetail]
    overridden_rules: List[RuleDetail]
    warnings: List[str]
    recommendations: List[str]


class LookupResponse(BaseModel):
    resolved_state: Optional[str]
    jurisdictions: List[dict]


class MaximumPossibleCreditSummary(BaseModel):
    jurisdiction: str
    base_credit_rate: float
    maximum_credit_rate: float
    maximum_credit_percent: float
    qualified_spend_assumption: Optional[float] = None
    maximum_credit_amount: Optional[float] = None
    required_conditions: List[str]
    stackable_components: List[dict]
    additional_benefits: List[dict]


class MaximumPossibleCreditResponse(BaseModel):
    summaries: List[MaximumPossibleCreditSummary]
    best_case_headline: Optional[str] = None
    generated_at: str


# -- Helpers -------------------------------------------------------------------

def _to_rule_detail(r) -> RuleDetail:
    return RuleDetail(
        jurisdiction_name=r.jurisdiction_name,
        rule_key=r.rule_key,
        rule_type=r.rule_type,
        raw_value=r.raw_value,
        value_unit=r.value_unit,
        computed_value=r.computed_value,
    )


# -- Routes --------------------------------------------------------------------

@router.post("", response_model=MaximizeResponse)
async def maximize(req: MaximizeRequest):
    if req.jurisdiction_codes is None and (req.lat is None or req.lng is None):
        raise HTTPException(status_code=422, detail="Provide either lat+lng or jurisdiction_codes")

    try:
        engine = _get_engine()
        result = engine.maximize(
            lat=req.lat,
            lng=req.lng,
            jurisdiction_codes=req.jurisdiction_codes,
            project_type=req.project_type,
            qualified_spend=req.qualified_spend,
            spend_by_location=req.spend_by_location,
        )
    except Exception as exc:
        logger.error(f"Maximizer error: {exc}")
        raise HTTPException(status_code=500, detail=f"Maximizer error: {exc}")

    return MaximizeResponse(
        resolved_state=result.resolved_state,
        jurisdictions_evaluated=result.jurisdictions_evaluated,
        qualified_spend=result.qualified_spend,
        total_incentive_usd=result.total_incentive_usd,
        effective_rate=result.effective_rate,
        breakdown=result.breakdown,
        applied_rules=[_to_rule_detail(r) for r in result.applied_rules],
        overridden_rules=[_to_rule_detail(r) for r in result.overridden_rules],
        warnings=result.warnings,
        recommendations=result.recommendations,
    )


@router.get("/lookup", response_model=LookupResponse)
async def lookup_jurisdictions(lat: float, lng: float):
    try:
        engine = _get_engine()
        jurisdictions, state_code = engine.resolve_jurisdictions_by_location(lat, lng)
    except Exception as exc:
        logger.error(f"Lookup error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return LookupResponse(
        resolved_state=state_code,
        jurisdictions=[
            {"id": j["id"], "name": j["name"], "code": j["code"], "type": j["type"]}
            for j in jurisdictions
        ],
    )


@router.get("/maximum-possible-credit", response_model=MaximumPossibleCreditResponse)
async def maximum_possible_credit(
    jurisdiction: Optional[str] = Query(default=None, description="Optional jurisdiction filter, e.g. New Jersey"),
    budget: Optional[float] = Query(default=None, gt=0, description="Optional total project budget in USD"),
):
    jurisdiction_query = (jurisdiction or "New Jersey").strip().lower()

    if jurisdiction_query not in {"new jersey", "nj"}:
        raise HTTPException(status_code=404, detail="Maximum credit summary currently configured for New Jersey only")

    base_rate = 0.30
    sub_jurisdiction_bonus = 0.05
    film_lease_partner_bonus = 0.10
    diversity_bonus = 0.02
    maximum_rate = base_rate + sub_jurisdiction_bonus + film_lease_partner_bonus + diversity_bonus

    stackable_components = [
        {
            "name": "Base Credit",
            "rate": base_rate,
            "percent": round(base_rate * 100, 2),
            "condition": "Project includes filming in New Jersey",
        },
        {
            "name": "Designated Municipality Bonus",
            "rate": sub_jurisdiction_bonus,
            "percent": round(sub_jurisdiction_bonus * 100, 2),
            "condition": "Project films in a designated municipality (e.g., Newark, Jersey City, Camden, Trenton)",
        },
        {
            "name": "Film-Lease Partner Facility Bonus",
            "rate": film_lease_partner_bonus,
            "percent": round(film_lease_partner_bonus * 100, 2),
            "condition": "Project qualifies as a film-lease production company at a designated facility",
        },
        {
            "name": "Diversity Bonus",
            "rate": diversity_bonus,
            "percent": round(diversity_bonus * 100, 2),
            "condition": "Diversity score is at least 20%",
        },
    ]

    required_conditions = [
        "Project includes filming in New Jersey",
        "Project films in a designated municipality",
        "Project qualifies as a film-lease production company at a designated facility",
        "Diversity score is at least 20%",
    ]

    additional_benefits = [
        {
            "type": "sales_tax_exemption",
            "rate": 0.06625,
            "description": "Certain tangible production purchases may qualify for New Jersey sales tax exemption",
        }
    ]

    qualified_spend_assumption = None
    maximum_credit_amount = None
    if budget is not None:
        qualified_spend_assumption = round(budget * 0.80, 2)
        maximum_credit_amount = round(qualified_spend_assumption * maximum_rate, 2)

    summary = MaximumPossibleCreditSummary(
        jurisdiction="New Jersey",
        base_credit_rate=round(base_rate, 4),
        maximum_credit_rate=round(maximum_rate, 4),
        maximum_credit_percent=round(maximum_rate * 100, 2),
        qualified_spend_assumption=qualified_spend_assumption,
        maximum_credit_amount=maximum_credit_amount,
        required_conditions=required_conditions,
        stackable_components=stackable_components,
        additional_benefits=additional_benefits,
    )

    return MaximumPossibleCreditResponse(
        summaries=[summary],
        best_case_headline="Up to 47.0% + sales tax exemption",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

