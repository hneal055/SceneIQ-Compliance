"""
Rule Engine Models (MVP)

Goal:
- Deterministic rule evaluation based on jurisdiction rule-config + expenses input.
- Keep models simple and stable; expand later.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


Money = Decimal


class ExpenseItem(BaseModel):
    category: str = Field(..., min_length=1, max_length=64)
    amount: Money = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=240)

    # Flags used by some rules (optional for MVP)
    is_payroll: Optional[bool] = None
    is_resident: Optional[bool] = None


class ProductionContext(BaseModel):
    title: Optional[str] = Field(None, max_length=120)
    budget: Optional[Money] = Field(None, gt=0)


class EvaluateRequest(BaseModel):
    jurisdiction_code: str = Field(..., min_length=1, max_length=10)
    production: Optional[ProductionContext] = None
    expenses: List[ExpenseItem] = Field(default_factory=list)


class RuleModel(BaseModel):
    id: str
    name: str
    type: Literal["tax_credit", "rebate", "grant", "placeholder"] = "tax_credit"

    # Core
    rate: Optional[Money] = None          # e.g. 0.30 for 30%
    cap_amount: Optional[Money] = None    # max credit/rebate amount
    min_spend: Optional[Money] = None     # minimum eligible spend required

    # Eligibility
    eligible_categories: List[str] = Field(default_factory=list)
    payroll_only: bool = False

    # Metadata
    notes: Optional[str] = None
    source_url: Optional[str] = None


class RuleSetModel(BaseModel):
    jurisdiction_code: str
    name: str
    country: str
    version: str = "0.1.0"
    effective_date: str = "2026-01-01"
    disclaimer: str = "MVP placeholders; not legal/tax advice."
    rules: List[RuleModel] = Field(default_factory=list)


class RuleBreakdown(BaseModel):
    rule_id: str
    rule_name: str
    rule_type: str
    eligible_spend: Money
    rate: Optional[Money] = None
    raw_amount: Optional[Money] = None
    applied_amount: Money
    capped: bool = False
    cap_amount: Optional[Money] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


class EvaluateResponse(BaseModel):
    jurisdiction_code: str
    total_eligible_spend: Money
    total_incentive_amount: Money
    breakdown: List[RuleBreakdown]
    warnings: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)




