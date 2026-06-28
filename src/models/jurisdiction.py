"""
Pydantic models for Jurisdictions
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class JurisdictionBase(BaseModel):
    """Base jurisdiction fields"""
    name: str = Field(..., description="Jurisdiction name (e.g., California)")
    code: str = Field(..., description="Jurisdiction code (e.g., CA)")
    country: str = Field(..., description="Country (e.g., USA)")
    type: str = Field(..., description="Type: state, province, or country")
    description: Optional[str] = Field(None, description="Description of jurisdiction")
    website: Optional[str] = Field(None, description="Official website URL")
    active: bool = Field(True, description="Whether jurisdiction is active")


class JurisdictionCreate(JurisdictionBase):
    """Model for creating a jurisdiction"""
    pass


class JurisdictionUpdate(BaseModel):
    """Model for updating a jurisdiction (all fields optional)"""
    name: Optional[str] = None
    code: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    active: Optional[bool] = None


class JurisdictionResponse(JurisdictionBase):
    """Model for jurisdiction responses"""
    id: str = Field(..., description="Unique identifier")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class JurisdictionList(BaseModel):
    """Model for list of jurisdictions"""
    total: int
    jurisdictions: list[JurisdictionResponse]




