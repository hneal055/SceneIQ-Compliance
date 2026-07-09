"""
Pydantic models for Tax Credit Calculator and Compliance Checker
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, List
from datetime import date


class SimpleCalculateRequest(BaseModel):
    """Request for simple tax credit calculation"""
    productionBudget: float = Field(..., description="Total production budget in USD", gt=0)
    jurisdictionId: str = Field(..., description="Jurisdiction ID")
    ruleId: str = Field(..., description="Incentive rule ID to apply")
    qualifyingBudget: Optional[float] = Field(None, description="Override qualifying budget (if different from total)")


class SimpleCalculateResponse(BaseModel):
    """Response for simple calculation"""
    jurisdiction: str = Field(..., description="Jurisdiction name")
    ruleName: str = Field(..., description="Incentive rule name")
    ruleCode: str = Field(..., description="Rule code")
    incentiveType: str = Field(..., description="Type of incentive")
    
    # Budget info
    totalBudget: float = Field(..., description="Total production budget")
    qualifyingBudget: float = Field(..., description="Budget that qualifies for incentive")
    
    # Rate info
    percentage: Optional[float] = Field(None, description="Incentive percentage rate")
    
    # Calculated amounts
    estimatedCredit: float = Field(..., description="Estimated tax credit/rebate amount")
    
    # Requirements check
    meetsMinimumSpend: bool = Field(..., description="Whether production meets minimum spend requirement")
    minimumSpendRequired: Optional[float] = Field(None, description="Minimum spend requirement")
    underMaximumCap: bool = Field(..., description="Whether credit is under maximum cap")
    maximumCapAmount: Optional[float] = Field(None, description="Maximum cap amount")
    
    # Additional info
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Additional requirements")
    notes: List[str] = Field(default_factory=list, description="Calculation notes and warnings")


class CompareCalculateRequest(BaseModel):
    """Request for comparing multiple jurisdictions.

    Provide EITHER production_id OR productionBudget:
    - production_id takes precedence; the comparison runs off the production's
      live-summed Expense records at request time. Any productionBudget /
      qualifyingBudget passed alongside it is ignored (a warning is logged).
    - productionBudget (+ optional qualifyingBudget) is the manual-entry path,
      unchanged from before.
    """
    productionBudget: Optional[float] = Field(None, description="Total production budget in USD (required unless production_id is provided)", gt=0)
    jurisdictionIds: List[str] = Field(..., description="List of jurisdiction IDs to compare", min_items=2, max_items=10)
    qualifyingBudget: Optional[float] = Field(None, description="Override qualifying budget")
    production_id: Optional[str] = Field(None, description="Compare a real production by ID; derives total/qualifying from its live Expense records (takes precedence over productionBudget/qualifyingBudget)")

    @model_validator(mode="after")
    def _require_budget_or_production(self):
        if not self.production_id and self.productionBudget is None:
            raise ValueError("Either production_id or productionBudget must be provided.")
        return self


class ComparisonResult(BaseModel):
    """Single jurisdiction comparison result"""
    jurisdiction: str
    jurisdictionId: str
    ruleName: str
    ruleCode: str
    incentiveType: str
    percentage: Optional[float]
    estimatedCredit: float
    meetsRequirements: bool
    rank: int
    savings: float


class CompareCalculateResponse(BaseModel):
    """Response for comparison calculation"""
    totalBudget: float
    comparisons: List[ComparisonResult]
    bestOption: ComparisonResult
    savingsVsWorst: float
    notes: List[str] = Field(default_factory=list)


# NEW: Compliance Checker Models

class ComplianceCheckRequest(BaseModel):
    """Request for compliance verification"""
    productionId: Optional[str] = Field(None, description="Production ID (if checking existing production)")
    ruleId: str = Field(..., description="Incentive rule ID to check compliance against")
    
    # Production details (if not using productionId)
    productionBudget: Optional[float] = Field(None, description="Total production budget", gt=0)
    qualifyingBudget: Optional[float] = Field(None, description="Qualifying budget")
    shootDays: Optional[int] = Field(None, description="Number of shoot days")
    crewSize: Optional[int] = Field(None, description="Total crew size")
    localHirePercentage: Optional[float] = Field(None, description="Percentage of local hires")
    
    # Compliance confirmations
    hasPromoLogo: Optional[bool] = Field(None, description="Has promotional logo in credits")
    hasCulturalTest: Optional[bool] = Field(None, description="Passed cultural test")
    isRelocating: Optional[bool] = Field(None, description="Is relocating production")
    additionalInfo: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional compliance info")


class RequirementCheck(BaseModel):
    """Single requirement check result"""
    requirement: str = Field(..., description="Requirement name")
    description: str = Field(..., description="What is required")
    status: str = Field(..., description="Status: met, not_met, unknown, not_applicable")
    required: bool = Field(..., description="Whether this is mandatory")
    userValue: Optional[Any] = Field(None, description="User's provided value")
    requiredValue: Optional[Any] = Field(None, description="Required value")
    notes: Optional[str] = Field(None, description="Additional notes")


class ComplianceCheckResponse(BaseModel):
    """Response for compliance check"""
    overallCompliance: str = Field(..., description="Overall status: compliant, non_compliant, partial, insufficient_data")
    jurisdiction: str = Field(..., description="Jurisdiction name")
    ruleName: str = Field(..., description="Rule name")
    ruleCode: str = Field(..., description="Rule code")
    
    # Summary
    totalRequirements: int = Field(..., description="Total requirements checked")
    requirementsMet: int = Field(..., description="Requirements met")
    requirementsNotMet: int = Field(..., description="Requirements not met")
    requirementsUnknown: int = Field(..., description="Requirements with unknown status")
    
    # Detailed checks
    requirements: List[RequirementCheck] = Field(..., description="Detailed requirement checks")
    
    # Estimated credit if compliant
    estimatedCredit: Optional[float] = Field(None, description="Estimated credit if compliant")
    
    # Action items
    actionItems: List[str] = Field(default_factory=list, description="What needs to be done")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    nextSteps: List[str] = Field(default_factory=list, description="Recommended next steps")


# Stackable Credits Models

class StackableCreditComponent(BaseModel):
    """Single component of a stackable credit"""
    ruleName: str = Field(..., description="Name of this credit component")
    ruleCode: str = Field(..., description="Rule code")
    ruleId: str = Field(..., description="Rule ID")
    incentiveType: str = Field(..., description="Type of incentive")
    percentage: Optional[float] = Field(None, description="Percentage rate")
    fixedAmount: Optional[float] = Field(None, description="Fixed amount")
    baseAmount: float = Field(..., description="Amount this applies to")
    creditAmount: float = Field(..., description="Credit from this component")
    isBase: bool = Field(default=False, description="Whether this is the base credit")
    stacksWith: Optional[str] = Field(None, description="What this stacks with")


class StackableCalculateRequest(BaseModel):
    """Request for stackable credit calculation"""
    productionBudget: float = Field(..., description="Total production budget", gt=0)
    jurisdictionId: str = Field(..., description="Jurisdiction ID")
    qualifyingBudget: Optional[float] = Field(None, description="Qualifying budget for base credit")
    localLaborBudget: Optional[float] = Field(None, description="Local resident labor budget")
    veteranLaborBudget: Optional[float] = Field(None, description="Veteran crew labor budget")
    diversitySpend: Optional[float] = Field(None, description="Qualified diversity spend")
    ruralSpend: Optional[float] = Field(None, description="Rural location spend")
    neighborIslandSpend: Optional[float] = Field(None, description="Neighbor island spend")


class StackableCalculateResponse(BaseModel):
    """Response for stackable credit calculation"""
    jurisdiction: str = Field(..., description="Jurisdiction name")
    totalBudget: float = Field(..., description="Total production budget")
    
    # Credit breakdown
    components: List[StackableCreditComponent] = Field(..., description="All credit components")
    
    # Totals
    totalCredits: float = Field(..., description="Total combined credits")
    effectiveRate: float = Field(..., description="Effective percentage rate")
    
    # Comparison
    baseCredit: float = Field(..., description="Base credit amount")
    bonusCredits: float = Field(..., description="Additional bonus credits")
    bonusValue: float = Field(..., description="Value of stacking bonuses")
    
    # Analysis
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Credit breakdown by type")
    notes: List[str] = Field(default_factory=list, description="Calculation notes")
    recommendations: List[str] = Field(default_factory=list, description="Optimization recommendations")


# Scenario Planning Models

class ScenarioCalculateRequest(BaseModel):
    """Request for scenario-based calculation"""
    productionBudget: float = Field(..., description="Total production budget", gt=0)
    jurisdictionId: str = Field(..., description="Jurisdiction ID")
    productionStartDate: Optional[date] = Field(None, description="Production start date (for date-based rules)")
    productionEndDate: Optional[date] = Field(None, description="Production end date")
    
    # Scenarios to test
    scenarios: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Different scenarios to model (e.g., different budgets, dates, hiring %)"
    )
    
    # Optional overrides
    qualifyingBudget: Optional[float] = Field(None, description="Qualifying budget")
    includeExpiredRules: bool = Field(default=False, description="Include expired rules in analysis")


class ScenarioResult(BaseModel):
    """Result for a single scenario"""
    scenarioName: str = Field(..., description="Scenario identifier")
    scenarioParams: Dict[str, Any] = Field(..., description="Parameters for this scenario")
    
    # Best rule for this scenario
    bestRuleName: str = Field(..., description="Best applicable rule")
    bestRuleCode: str = Field(..., description="Rule code")
    ruleId: str = Field(..., description="Rule ID")
    
    # Results
    estimatedCredit: float = Field(..., description="Estimated credit")
    effectiveRate: float = Field(..., description="Effective percentage rate")
    meetsRequirements: bool = Field(..., description="Whether requirements are met")
    
    # Rule details
    isActive: bool = Field(..., description="Whether rule is currently active")
    isExpired: bool = Field(default=False, description="Whether rule has expired")
    effectiveDate: Optional[date] = Field(None, description="Rule effective date")
    expirationDate: Optional[date] = Field(None, description="Rule expiration date")
    
    # Analysis
    notes: List[str] = Field(default_factory=list, description="Scenario notes")


class ScenarioCalculateResponse(BaseModel):
    """Response for scenario analysis"""
    jurisdiction: str = Field(..., description="Jurisdiction name")
    baseProductionBudget: float = Field(..., description="Base production budget")
    productionDate: Optional[date] = Field(None, description="Production date analyzed")
    
    # Scenario results
    scenarios: List[ScenarioResult] = Field(..., description="All scenario results")
    bestScenario: ScenarioResult = Field(..., description="Best scenario")
    worstScenario: ScenarioResult = Field(..., description="Worst scenario")
    
    # Analysis
    savingsDifference: float = Field(..., description="Savings difference between best and worst")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    
    # Available rules summary
    availableRules: int = Field(..., description="Number of available rules")
    expiredRules: int = Field(default=0, description="Number of expired rules")


class DateBasedRulesRequest(BaseModel):
    """Request for date-based rule selection"""
    jurisdictionId: str = Field(..., description="Jurisdiction ID")
    productionDate: date = Field(..., description="Date to check rules for")
    includeExpired: bool = Field(default=False, description="Include expired rules")


class DateBasedRulesResponse(BaseModel):
    """Response showing rules available on a specific date"""
    jurisdiction: str = Field(..., description="Jurisdiction name")
    queryDate: date = Field(..., description="Date queried")
    
    # Rules breakdown
    activeRules: List[Dict[str, Any]] = Field(..., description="Active rules on this date")
    upcomingRules: List[Dict[str, Any]] = Field(default_factory=list, description="Rules becoming active soon")
    expiredRules: List[Dict[str, Any]] = Field(default_factory=list, description="Recently expired rules")
    
    # Summary
    totalActive: int = Field(..., description="Number of active rules")
    totalUpcoming: int = Field(default=0, description="Number of upcoming rules")
    totalExpired: int = Field(default=0, description="Number of expired rules")
    
    notes: List[str] = Field(default_factory=list, description="Important date-related notes")




