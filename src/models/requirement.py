"""Pydantic models for JurisdictionRequirement."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RequirementBase(BaseModel):
    name: str
    category: str = Field(
        description="permit | insurance | registration | designation | infrastructure | portal | contact | other"
    )
    requirementType: str = Field(
        default="mandatory",
        description="mandatory | recommended | informational",
    )
    description: str
    applicableTo: List[str] = Field(
        default_factory=list,
        description="Project types this applies to. Empty = all types.",
    )
    contactInfo: Optional[str] = None
    portalUrl: Optional[str] = None
    sourceUrl: Optional[str] = None
    extractedBy: str = Field(default="manual")
    active: bool = True


class RequirementCreate(RequirementBase):
    jurisdictionId: str


class RequirementUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    requirementType: Optional[str] = None
    description: Optional[str] = None
    applicableTo: Optional[List[str]] = None
    contactInfo: Optional[str] = None
    portalUrl: Optional[str] = None
    sourceUrl: Optional[str] = None
    active: Optional[bool] = None


class RequirementResponse(RequirementBase):
    id: str
    jurisdictionId: str
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)


class ChecklistItem(RequirementResponse):
    """A requirement in a checklist response, annotated with its origin."""
    fromParent: bool = False
    parentJurisdictionCode: Optional[str] = None
    parentJurisdictionName: Optional[str] = None


class ChecklistResponse(BaseModel):
    jurisdictionCode: str
    jurisdictionName: str
    projectType: Optional[str]
    total: int
    byCategory: dict  # category -> count
    requirements: List[ChecklistItem]



