"""
Pydantic models for PDF Report Generation
"""
from pydantic import BaseModel, Field
from typing import Optional


class GenerateComparisonReportRequest(BaseModel):
    """Request to generate jurisdiction comparison report"""
    productionTitle: str = Field(..., description="Production title")
    budget: float = Field(..., description="Production budget", gt=0)
    jurisdictionIds: list[str] = Field(..., description="List of jurisdiction IDs to compare", min_items=2, max_items=10)


class GenerateComplianceReportRequest(BaseModel):
    """Request to generate compliance report"""
    productionTitle: str = Field(..., description="Production title")
    ruleId: str = Field(..., description="Incentive rule ID")
    productionBudget: float = Field(..., description="Production budget", gt=0)
    shootDays: Optional[int] = Field(None, description="Number of shoot days")
    localHirePercentage: Optional[float] = Field(None, description="Local hire percentage")
    hasPromoLogo: Optional[bool] = Field(None, description="Has promotional logo")
    hasCulturalTest: Optional[bool] = Field(None, description="Passed cultural test")


class GenerateScenarioReportRequest(BaseModel):
    """Request to generate scenario analysis report"""
    productionTitle: str = Field(..., description="Production title")
    jurisdictionId: str = Field(..., description="Jurisdiction ID")
    baseProductionBudget: float = Field(..., description="Base production budget", gt=0)
    scenarios: list[dict] = Field(..., description="List of scenarios to analyze", min_items=2)


class ReportResponse(BaseModel):
    """Response with PDF report"""
    message: str = Field(..., description="Success message")
    filename: str = Field(..., description="Generated filename")
    reportType: str = Field(..., description="Type of report generated")



