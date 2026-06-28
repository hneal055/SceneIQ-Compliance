"""
Stacking Engine API â€” combine state + sub-jurisdiction incentives for a production scenario.

POST /stacking-engine/calculate
  â†’ Returns a full incentive stack: state base + county bonuses, total value, warnings.

POST /stacking-engine/compare
  â†’ Compare two or more jurisdiction stacks side by side.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stacking-engine", tags=["Stacking Engine"])


# â”€â”€ Request / response models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ScenarioInput(BaseModel):
    production_id:       Optional[str] = None
    jurisdiction_code:   str
    qualified_spend:     float  = Field(..., gt=0, description="Total qualified expenditure in USD")
    local_hire_percent:  Optional[float] = Field(None, ge=0, le=100)
    shooting_days:       Optional[int]   = Field(None, ge=0)
    production_start:    Optional[str]   = None   # ISO date YYYY-MM-DD


class StackLayer(BaseModel):
    source:          str    # 'state_incentive_rule' | 'local_rule'
    name:            str
    code:            str
    category:        str
    rule_type:       str
    rate:            Optional[float]
    fixed_amount:    Optional[float]
    incentive_value: float
    notes:           Optional[str] = None


class StackResult(BaseModel):
    jurisdiction_code:   str
    jurisdiction_name:   str
    qualified_spend:     float
    layers:              list[StackLayer]
    total_incentive:     float
    effective_rate:      float
    warnings:            list[str]


class CalculateRequest(BaseModel):
    scenario: ScenarioInput


class CompareRequest(BaseModel):
    scenarios: list[ScenarioInput] = Field(..., min_length=2, max_length=6)


# â”€â”€ Core stacking logic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except ValueError:
        return None


def _is_active_on(effective_date: Optional[datetime], expiration_date: Optional[datetime], check_date: date) -> bool:
    if effective_date and check_date < effective_date.date():
        return False
    if expiration_date and check_date > expiration_date.date():
        return False
    return True


async def _compute_stack(scenario: ScenarioInput) -> StackResult:
    today = _parse_date(scenario.production_start) or date.today()
    qs = Decimal(str(scenario.qualified_spend))
    warnings: list[str] = []
    layers: list[StackLayer] = []

    # â”€â”€ 1. Look up jurisdiction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    jur = await prisma.jurisdiction.find_unique(
        where={"code": scenario.jurisdiction_code},
        include={
            "incentiveRules": True,
            "localRules": True,
        },
    )

    if not jur:
        # Try as a sub-jurisdiction (county/city) â€” look up parent
        jur = await prisma.jurisdiction.find_first(
            where={"code": scenario.jurisdiction_code},
        )
        if not jur:
            raise HTTPException(status_code=404, detail=f"Jurisdiction '{scenario.jurisdiction_code}' not found")

    # â”€â”€ 2. If this is a sub-jurisdiction, also load parent state rules â”€â”€â”€â”€â”€â”€â”€â”€
    parent_rules = []
    if jur.parentId:
        parent = await prisma.jurisdiction.find_unique(
            where={"id": jur.parentId},
            include={"incentiveRules": True},
        )
        if parent:
            parent_rules = parent.incentiveRules or []
            # Check inheritance policy
            policy = await prisma.inheritancepolicy.find_first(
                where={"childJurisdictionId": jur.id, "parentJurisdictionId": jur.parentId},
            )
            if policy and policy.policyType == "additive":
                # Stack parent state rules on top
                for rule in parent_rules:
                    if not rule.active:
                        continue
                    if not _is_active_on(rule.effectiveDate, rule.expirationDate, today):
                        warnings.append(f"State rule '{rule.ruleName}' is outside its effective date range â€” skipped")
                        continue
                    incentive = _calc_incentive(rule.percentage, rule.fixedAmount, rule.maxCredit, qs)
                    if incentive > 0:
                        layers.append(StackLayer(
                            source="state_incentive_rule",
                            name=rule.ruleName,
                            code=rule.ruleCode,
                            category=rule.incentiveType,
                            rule_type=rule.creditType or "refundable",
                            rate=rule.percentage,
                            fixed_amount=rule.fixedAmount,
                            incentive_value=float(incentive),
                            notes=f"Inherited from {parent.name} (additive policy)",
                        ))

    # â”€â”€ 3. State-level incentive rules â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    state_rules = jur.incentiveRules or []
    for rule in state_rules:
        if not rule.active:
            continue
        if not _is_active_on(rule.effectiveDate, rule.expirationDate, today):
            warnings.append(f"Rule '{rule.ruleName}' is outside its effective date range â€” skipped")
            continue

        # Min spend check
        if rule.minSpend and qs < Decimal(str(rule.minSpend)):
            warnings.append(
                f"Rule '{rule.ruleName}' requires min spend ${rule.minSpend:,.0f} "
                f"â€” qualified spend ${float(qs):,.0f} is below threshold"
            )
            continue

        incentive = _calc_incentive(rule.percentage, rule.fixedAmount, rule.maxCredit, qs)
        if incentive > 0:
            layers.append(StackLayer(
                source="state_incentive_rule",
                name=rule.ruleName,
                code=rule.ruleCode,
                category=rule.incentiveType,
                rule_type=rule.creditType or "refundable",
                rate=rule.percentage,
                fixed_amount=rule.fixedAmount,
                incentive_value=float(incentive),
            ))

    # â”€â”€ 4. Local rules (county/city approved rules) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    local_rules = jur.localRules or []
    active_local = [r for r in local_rules if r.active]

    if not active_local and not jur.parentId:
        warnings.append("No local rules found for this jurisdiction â€” only state rules applied")

    for rule in active_local:
        if not _is_active_on(rule.effectiveDate, rule.expirationDate, today):
            warnings.append(f"Local rule '{rule.name}' is expired or not yet effective â€” skipped")
            continue

        # Local hire check
        if scenario.local_hire_percent is not None and rule.requirements:
            req_lower = rule.requirements.lower()
            if "local hire" in req_lower or "local crew" in req_lower:
                if scenario.local_hire_percent < 75:
                    warnings.append(
                        f"Local rule '{rule.name}' may require local hire â€” "
                        f"provided {scenario.local_hire_percent:.0f}% (verify requirement)"
                    )

        incentive = _calc_incentive(rule.percentage, rule.amount, None, qs)
        if incentive > 0:
            layers.append(StackLayer(
                source="local_rule",
                name=rule.name,
                code=rule.code,
                category=rule.category,
                rule_type=rule.ruleType,
                rate=rule.percentage,
                fixed_amount=rule.amount,
                incentive_value=float(incentive),
                notes=f"Extracted by {rule.extractedBy}" if rule.extractedBy != "manual" else None,
            ))

    # â”€â”€ 5. Aggregate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    total = sum(Decimal(str(l.incentive_value)) for l in layers)
    effective_rate = float(total / qs) if qs > 0 else 0.0

    if not layers:
        warnings.append("No applicable incentive rules found for this scenario")

    return StackResult(
        jurisdiction_code=jur.code,
        jurisdiction_name=jur.name,
        qualified_spend=float(qs),
        layers=layers,
        total_incentive=float(total),
        effective_rate=round(effective_rate, 4),
        warnings=warnings,
    )


def _calc_incentive(
    percentage: Optional[float],
    fixed_amount: Optional[float],
    max_credit: Optional[float],
    qualified_spend: Decimal,
) -> Decimal:
    if percentage:
        value = qualified_spend * Decimal(str(percentage)) / Decimal("100")
    elif fixed_amount:
        value = Decimal(str(fixed_amount))
    else:
        return Decimal("0")

    if max_credit:
        value = min(value, Decimal(str(max_credit)))

    return value


# â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/calculate", summary="Calculate full incentive stack for a scenario")
async def calculate_stack(request: CalculateRequest):
    result = await _compute_stack(request.scenario)
    return result


@router.post("/compare", summary="Compare incentive stacks across jurisdictions")
async def compare_stacks(request: CompareRequest):
    results = []
    for scenario in request.scenarios:
        try:
            result = await _compute_stack(scenario)
            results.append(result)
        except HTTPException as e:
            results.append({
                "jurisdiction_code": scenario.jurisdiction_code,
                "error": e.detail,
            })

    # Sort by total incentive descending
    results.sort(key=lambda r: r.total_incentive if isinstance(r, StackResult) else -1, reverse=True)

    best = results[0] if results and isinstance(results[0], StackResult) else None

    return {
        "scenarios": results,
        "best_jurisdiction": best.jurisdiction_code if best else None,
        "best_total_incentive": best.total_incentive if best else 0,
        "best_effective_rate": best.effective_rate if best else 0,
    }


@router.get("/jurisdictions-with-local-rules", summary="List jurisdictions that have active local rules")
async def jurisdictions_with_local_rules():
    """Returns jurisdictions that have approved local rules ready for stacking."""
    results = await prisma.query_raw(
        """
        SELECT j.id, j.name, j.code, j.type, j."parentId",
               COUNT(lr.id) as local_rule_count
        FROM jurisdictions j
        JOIN local_rules lr ON lr."jurisdictionId" = j.id AND lr.active = true
        GROUP BY j.id, j.name, j.code, j.type, j."parentId"
        ORDER BY local_rule_count DESC
        """
    )
    return {"jurisdictions": results}





