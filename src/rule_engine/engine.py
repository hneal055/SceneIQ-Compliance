from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from .models import EvaluateRequest, EvaluateResponse
from .registry import get_rule_path


@dataclass
class EvalResult:
    eligible: bool
    benefit_amount: Decimal
    qualified_spend_total: Decimal
    compliance_flags: List[str]
    trace: List[Dict[str, Any]]


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.fromisoformat(s).date()


def _dec(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    if v is None:
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def load_rule_from_file(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def evaluate_rule(
    *,
    rule: Dict[str, Any],
    jurisdiction_code: str,
    production_start_date: Optional[str],
    expenses: List[Dict[str, Any]],
) -> EvalResult:
    trace: List[Dict[str, Any]] = []
    flags: List[str] = []

    if not rule.get("active", False):
        return EvalResult(False, Decimal("0"), Decimal("0"), ["RULE_INACTIVE"], [{"step": "rule_inactive"}])

    if jurisdiction_code.strip().upper() != str(rule.get("jurisdiction_code", "")).strip().upper():
        return EvalResult(False, Decimal("0"), Decimal("0"), ["JURISDICTION_MISMATCH"], [{"step": "jurisdiction_mismatch"}])

    eff_from = _parse_date(rule.get("effective_from"))
    eff_to = _parse_date(rule.get("effective_to"))
    prod_date = _parse_date(production_start_date) if production_start_date else None

    if prod_date and eff_from and prod_date < eff_from:
        return EvalResult(False, Decimal("0"), Decimal("0"), ["OUTSIDE_EFFECTIVE_DATES"], [{"step": "prod_before_effective_from"}])
    if prod_date and eff_to and prod_date > eff_to:
        return EvalResult(False, Decimal("0"), Decimal("0"), ["OUTSIDE_EFFECTIVE_DATES"], [{"step": "prod_after_effective_to"}])

    eligibility = rule.get("eligibility", {}) or {}
    calc = rule.get("calculation", {}) or {}

    qualified_categories = {str(x).strip().lower() for x in (eligibility.get("qualified_categories", []) or [])}
    exclude_categories = {str(x).strip().lower() for x in (eligibility.get("exclude_categories", []) or [])}
    in_state_required = bool(eligibility.get("in_state_required", False))
    labor_residency_required = bool(eligibility.get("labor_residency_required", False))
    min_qualified_spend = _dec(eligibility.get("min_qualified_spend", 0) or 0)

    qualified_total = Decimal("0")
    counted = 0
    skipped = 0

    for e in expenses:
        amount = _dec(e.get("amount", 0) or 0)
        category = str(e.get("category", "") or "").strip().lower()

        is_qualified = bool(e.get("qualified", True))
        in_state = bool(e.get("in_state", True))
        is_labor = bool(e.get("labor", False))
        is_resident = bool(e.get("resident", True))

        if qualified_categories and category not in qualified_categories:
            skipped += 1
            continue
        if exclude_categories and category in exclude_categories:
            skipped += 1
            continue

        if not is_qualified:
            skipped += 1
            continue
        if in_state_required and not in_state:
            skipped += 1
            continue
        if labor_residency_required and is_labor and not is_resident:
            skipped += 1
            continue

        qualified_total += amount
        counted += 1

    trace.append({"step": "compute_qualified_total", "qualified_total": str(qualified_total), "counted": counted, "skipped": skipped})

    if min_qualified_spend and qualified_total < min_qualified_spend:
        flags.append("BELOW_MIN_QUALIFIED_SPEND")
        trace.append({"step": "min_spend_failed", "min_required": str(min_qualified_spend), "actual": str(qualified_total)})
        return EvalResult(False, Decimal("0"), qualified_total, flags, trace)

    rate = _dec(calc.get("rate", 0) or 0)
    base = str(calc.get("base", "qualified_spend_total"))

    base_total = qualified_total
    if base != "qualified_spend_total":
        flags.append("BASE_FALLBACK_TO_QUALIFIED_SPEND_TOTAL")
        trace.append({"step": "base_fallback", "requested_base": base, "used_base": "qualified_spend_total"})

    benefit = base_total * rate
    trace.append({"step": "apply_rate", "rate": str(rate), "base_total": str(base_total), "benefit_pre_cap": str(benefit)})

    caps = calc.get("caps", {}) or {}
    max_benefit = caps.get("max_benefit", None)
    if max_benefit is not None:
        max_benefit_d = _dec(max_benefit)
        if benefit > max_benefit_d:
            benefit = max_benefit_d
            flags.append("CAPPED_MAX_BENEFIT")
            trace.append({"step": "cap_applied", "max_benefit": str(max_benefit_d), "benefit_post_cap": str(benefit)})

    return EvalResult(True, benefit, qualified_total, flags, trace)


def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    """
    Entry point used by tests + API.

    Test contract:
      - Unknown jurisdiction MUST raise FileNotFoundError
      - EvaluateResponse.breakdown is a LIST of items requiring:
          rule_id, rule_name, rule_type, applied_amount
    """
    code = (getattr(req, "jurisdiction_code", "") or "").strip().upper()
    rule_path = get_rule_path(code)

    if not rule_path:
        raise FileNotFoundError(f"No rule file found for jurisdiction: {code}")

    rule = load_rule_from_file(rule_path)

    production_start_date = (
        getattr(req, "production_start_date", None)
        or getattr(req, "production", None)
        or None
    )

    expenses_payload: List[Dict[str, Any]] = []
    for e in getattr(req, "expenses", []) or []:
        expenses_payload.append(
            {
                "category": getattr(e, "category", None),
                "amount": getattr(e, "amount", None),
                "qualified": True,
                "labor": bool(getattr(e, "is_payroll", False)),
                "in_state": True,
                "resident": True,
            }
        )

    result = evaluate_rule(
        rule=rule,
        jurisdiction_code=code,
        production_start_date=production_start_date,
        expenses=expenses_payload,
    )

    # Required breakdown fields (pull from rule json if present)
    rule_id = str(rule.get("id") or rule.get("rule_id") or f"{code}-MVP")
    rule_name = str(rule.get("name") or rule.get("rule_name") or f"{code} Incentive Rule")
    rule_type = str(rule.get("type") or rule.get("rule_type") or "credit")

    breakdown_item = {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "rule_type": rule_type,
        "applied_amount": result.benefit_amount,
        # Extra keys are fine if your model allows them; if not, pydantic will ignore only if configured.
        "eligible_spend": result.qualified_spend_total,
        "rate_applied": _dec((rule.get("calculation", {}) or {}).get("rate", 0) or 0),
        "base": "qualified_spend_total",
    }

    payload: Dict[str, Any] = {
        "jurisdiction_code": code,
        "eligible": result.eligible,
        "qualified_spend_total": result.qualified_spend_total,
        "benefit_amount": result.benefit_amount,
        "compliance_flags": result.compliance_flags,
        "trace": result.trace,
        "total_eligible_spend": result.qualified_spend_total,
        "total_incentive_amount": result.benefit_amount,
        "breakdown": [breakdown_item],
    }

    return EvaluateResponse.model_validate(payload)



