"""
Pydantic models for Productions
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ProductionBase(BaseModel):
    """Base production fields"""
    title: str = Field(..., description="Production title")
    productionType: str = Field(..., description="Type: feature, tv_series, commercial, documentary")
    jurisdictionId: str = Field(..., description="Jurisdiction ID where production is based")
    budgetTotal: float = Field(..., description="Total production budget in USD")
    budgetQualifying: Optional[float] = Field(None, description="Qualifying budget for incentives")
    startDate: datetime = Field(..., description="Production start date")
    endDate: Optional[datetime] = Field(None, description="Production end date")
    productionCompany: str = Field(..., description="Production company name")
    episodeCount: Optional[int] = Field(None, description="Episode count (TV series only)")
    contact: Optional[str] = Field(None, description="Contact information")
    status: str = Field(..., description="Status: planning, pre_production, production, post_production, completed")
    metadata: Optional[str] = Field(None, description="Additional metadata as JSON string")


class ProductionCreate(ProductionBase):
    """Model for creating a production"""
    pass


class ProductionUpdate(BaseModel):
    """Model for updating a production"""
    title: Optional[str] = None
    productionType: Optional[str] = None
    jurisdictionId: Optional[str] = None
    budgetTotal: Optional[float] = None
    budgetQualifying: Optional[float] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    productionCompany: Optional[str] = None
    episodeCount: Optional[int] = None
    contact: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[str] = None


class ProductionResponse(ProductionBase):
    """Model for production responses"""
    id: str
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True


class ProductionList(BaseModel):
    """Model for list of productions"""
    total: int
    productions: List[ProductionResponse]

