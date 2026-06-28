"""
Pydantic models for Incentive Rules

Key fix: 
- Postgres column `requirements` is TEXT, so Prisma/DB may return it as a JSON string. 
- FastAPI response models expect a dict => ResponseValidationError unless we coerce. 
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Pydantic v2 preferred config (with a soft fallback pattern)
try:
    from pydantic import ConfigDict, field_validator
    _HAS_V2 = True
except Exception:  # pragma: no cover
    ConfigDict = None  # type: ignore
    field_validator = None  # type: ignore
    _HAS_V2 = False


RequirementsValue = Dict[str, Any]
RequirementsInput = Union[RequirementsValue, str, None]


def _coerce_requirements(value: RequirementsInput) -> RequirementsValue:
    """
    Coerce requirements into a dict. 

    Accepts:
      - dict -> dict
      - JSON string -> dict (if valid)
      - None / "" -> {}
      - anything else -> {}
    """
    if value is None: 
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _coerce_string_list(value: Any) -> List[str]:
    """
    Coerce list-like fields to a list of strings. 
    - None -> []
    - list[str] -> list[str]
    - list[Any] -> list[str] (stringified)
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if x is not None]
    return []


class IncentiveRuleBase(BaseModel):
    """
    Base incentive rule fields. 

    Note: DB schema includes a `fixedAmount` column; included here for completeness.
    """
    jurisdictionId: str = Field(..., description="Jurisdiction ID this rule belongs to")
    ruleName: str = Field(..., description="Name of the incentive rule")
    ruleCode: str = Field(..., description="Internal reference code (unique)")
    incentiveType: str = Field(..., description="Type: tax_credit, rebate, grant, exemption")

    # Numeric fields - percentage stored as whole number (25.0 = 25%)
    percentage: Optional[float] = Field(None, description="Percentage rate (e. g., 25.0 for 25%)")
    fixedAmount: Optional[float] = Field(None, description="Fixed amount incentive (if applicable)")
    minSpend: Optional[float] = Field(None, description="Minimum spend required")
    maxCredit: Optional[float] = Field(None, description="Maximum credit cap")

    # Arrays
    eligibleExpenses: List[str] = Field(default_factory=list, description="Eligible expense categories")
    excludedExpenses: List[str] = Field(default_factory=list, description="Excluded expense categories")

    # Dates
    effectiveDate: datetime = Field(..., description="When rule becomes effective")
    expirationDate: Optional[datetime] = Field(None, description="When rule expires")

    # Requirements (stored as TEXT in DB; may arrive as JSON string)
    requirements: RequirementsValue = Field(default_factory=dict, description="Additional requirements")

    active: bool = Field(default=True, description="Whether rule is active")

    # --- Validators (Pydantic v2) ---
    if _HAS_V2:

        @field_validator("requirements", mode="before")
        @classmethod
        def _validate_requirements(cls, v: Any) -> RequirementsValue:
            return _coerce_requirements(v)

        @field_validator("eligibleExpenses", mode="before")
        @classmethod
        def _validate_eligible_expenses(cls, v: Any) -> List[str]:
            return _coerce_string_list(v)

        @field_validator("excludedExpenses", mode="before")
        @classmethod
        def _validate_excluded_expenses(cls, v: Any) -> List[str]:
            return _coerce_string_list(v)


class IncentiveRuleCreate(IncentiveRuleBase):
    """Model for creating an incentive rule."""
    pass


class IncentiveRuleUpdate(BaseModel):
    """Model for updating an incentive rule (all fields optional)."""
    jurisdictionId: Optional[str] = None
    ruleName: Optional[str] = None
    ruleCode: Optional[str] = None
    incentiveType: Optional[str] = None

    percentage: Optional[float] = None
    fixedAmount: Optional[float] = None
    minSpend: Optional[float] = None
    maxCredit: Optional[float] = None

    eligibleExpenses: Optional[List[str]] = None
    excludedExpenses: Optional[List[str]] = None

    effectiveDate: Optional[datetime] = None
    expirationDate: Optional[datetime] = None

    # allow dict OR json-string on update as well
    requirements: Optional[RequirementsValue] = None

    active: Optional[bool] = None

    if _HAS_V2:

        @field_validator("requirements", mode="before")
        @classmethod
        def _validate_requirements(cls, v: Any) -> Optional[RequirementsValue]: 
            if v is None:
                return None
            return _coerce_requirements(v)

        @field_validator("eligibleExpenses", mode="before")
        @classmethod
        def _validate_eligible_expenses(cls, v: Any) -> Optional[List[str]]:
            if v is None:
                return None
            return _coerce_string_list(v)

        @field_validator("excludedExpenses", mode="before")
        @classmethod
        def _validate_excluded_expenses(cls, v: Any) -> Optional[List[str]]:
            if v is None:
                return None
            return _coerce_string_list(v)


class IncentiveRuleResponse(IncentiveRuleBase):
    """Model for incentive rule responses."""
    id: str
    createdAt:  datetime
    updatedAt: datetime

    # Pydantic v2 config
    if _HAS_V2:
        model_config = ConfigDict(from_attributes=True)  # type: ignore[misc]
    else:
        class Config:  # pragma: no cover
            from_attributes = True


class IncentiveRuleList(BaseModel):
    """Model for list of incentive rules."""
    total: int = Field(..., description="Total number of rules available")
    page: int = Field(1, description="Current page number")
    pageSize: int = Field(... , description="Number of items per page")
    totalPages: int = Field(... , description="Total number of pages")
    rules: List[IncentiveRuleResponse] = Field(default_factory=list, description="Rules returned")



