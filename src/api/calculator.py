"""
Calculator API endpoints - Tax credit calculations
"""
from fastapi import APIRouter, HTTPException, status
import json
import logging
from typing import Dict, Any
from pydantic import BaseModel

from src.models.calculator import (
    SimpleCalculateRequest,
    SimpleCalculateResponse,
    CompareCalculateRequest,
    CompareCalculateResponse,
    ComparisonResult,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    RequirementCheck,
    StackableCalculateRequest,
    StackableCalculateResponse,
    StackableCreditComponent,
    ScenarioCalculateRequest,
    ScenarioCalculateResponse,
    ScenarioResult,
    DateBasedRulesRequest,
    DateBasedRulesResponse
)
from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calculate", tags=["Calculator"])


class QuickCalcRequest(BaseModel):
    production_id: str
    jurisdiction_id: str


@router.post("", summary="Quick calculation: production + jurisdiction â†’ incentive estimate")
async def calculate_quick(request: QuickCalcRequest):
    """
    Calculate estimated tax credit given a production ID and jurisdiction ID.
    Uses production's budgetTotal/budgetQualifying and the jurisdiction's first active incentive rule.
    """
    production = await prisma.production.find_unique(where={"id": request.production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    rules = await prisma.incentiverule.find_many(
        where={"jurisdictionId": request.jurisdiction_id, "active": True},
        order={"percentage": "desc"},
        take=1,
    )

    total_expenses = production.budgetTotal
    qualified_expenses = production.budgetQualifying if production.budgetQualifying else total_expenses * 0.8
    rate = (rules[0].percentage / 100) if rules and rules[0].percentage else 0.20
    max_credit = rules[0].maxCredit if rules and rules[0].maxCredit else float("inf")
    incentive_amount = min(qualified_expenses * rate, max_credit)
    effective_rate = incentive_amount / qualified_expenses if qualified_expenses > 0 else 0.0

    return {
        "production_id": request.production_id,
        "jurisdiction_id": request.jurisdiction_id,
        "total_expenses": total_expenses,
        "qualified_expenses": qualified_expenses,
        "incentive_amount": incentive_amount,
        "effective_rate": effective_rate,
    }


def parse_json_field(field: Any) -> Dict:
    """Parse JSON field that might be string or dict"""
    if isinstance(field, str):
        return json.loads(field)
    return field if field else {}


@router.post("/simple", response_model=SimpleCalculateResponse, summary="Calculate tax credit for single rule")
async def calculate_simple(request: SimpleCalculateRequest):
    """
    Calculate estimated tax credit for a production using a specific incentive rule.
    
    - **productionBudget**: Total production budget
    - **jurisdictionId**: Target jurisdiction
    - **ruleId**: Specific incentive rule to apply
    - **qualifyingBudget**: Optional override for qualifying budget
    
    Returns detailed calculation with requirements check.
    """
    
    # Get jurisdiction
    jurisdiction = await prisma.jurisdiction.find_unique(
        where={"id": request.jurisdictionId}
    )
    
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Jurisdiction not found"
        )
    
    # Get rule
    rule = await prisma.incentiverule.find_unique(
        where={"id": request.ruleId}
    )
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incentive rule not found"
        )
    
    # Verify rule belongs to jurisdiction
    if rule.jurisdictionId != request.jurisdictionId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rule does not belong to specified jurisdiction"
        )
    
    # Use qualifying budget or default to total budget
    qualifying_budget = request.qualifyingBudget if request.qualifyingBudget else request.productionBudget
    
    # Calculate credit
    if rule.percentage:
        estimated_credit = qualifying_budget * (rule.percentage / 100)
    elif rule.fixedAmount:
        estimated_credit = rule.fixedAmount
    else:
        estimated_credit = 0
    
    # Check minimum spend
    meets_minimum = True
    if rule.minSpend:
        meets_minimum = qualifying_budget >= rule.minSpend
        if not meets_minimum:
            estimated_credit = 0
    
    # Apply maximum cap
    under_maximum = True
    if rule.maxCredit and estimated_credit > rule.maxCredit:
        estimated_credit = rule.maxCredit
        under_maximum = False
    
    # Parse requirements
    requirements = parse_json_field(rule.requirements)
    
    # Generate notes
    notes = []
    if not meets_minimum:
        notes.append(f"âš ï¸ Does not meet minimum spend requirement of ${rule.minSpend:,.0f}")
    if not under_maximum:
        notes.append(f"â„¹ï¸ Credit capped at maximum of ${rule.maxCredit:,.0f}")
    if rule.percentage:
        notes.append(f"ðŸ’¡ Rate: {rule.percentage}% of qualifying budget")
    if requirements:
        notes.append(f"ðŸ“‹ Additional requirements apply - see requirements field")
    
    return SimpleCalculateResponse(
        jurisdiction=jurisdiction.name,
        ruleName=rule.ruleName,
        ruleCode=rule.ruleCode,
        incentiveType=rule.incentiveType,
        totalBudget=request.productionBudget,
        qualifyingBudget=qualifying_budget,
        percentage=rule.percentage,
        estimatedCredit=estimated_credit,
        meetsMinimumSpend=meets_minimum,
        minimumSpendRequired=rule.minSpend,
        underMaximumCap=under_maximum,
        maximumCapAmount=rule.maxCredit,
        requirements=requirements,
        notes=notes
    )


@router.post("/compare", response_model=CompareCalculateResponse, summary="Compare tax credits across jurisdictions")
async def calculate_compare(request: CompareCalculateRequest):
    """
    Compare estimated tax credits across multiple jurisdictions.
    
    - **productionBudget**: Total production budget
    - **jurisdictionIds**: List of 2-10 jurisdictions to compare
    - **qualifyingBudget**: Optional override for qualifying budget
    
    Returns ranked comparison of all jurisdictions with best recommendation.
    """
    
    if len(request.jurisdictionIds) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must compare at least 2 jurisdictions"
        )
    
    if len(request.jurisdictionIds) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare more than 10 jurisdictions at once"
        )
    
    # Get all jurisdictions
    jurisdictions = await prisma.jurisdiction.find_many(
        where={"id": {"in": request.jurisdictionIds}}
    )
    
    if len(jurisdictions) != len(request.jurisdictionIds):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more jurisdictions not found"
        )

    # Resolve the budget figures from one of two mutually-exclusive sources:
    #   1. production_id  -> live-sum the production's Expense records right now
    #      (never a cached/stored budget field: expenses can be reclassified
    #      after import, so a cached number would go stale)
    #   2. productionBudget / qualifyingBudget -> manual entry (unchanged path)
    if request.production_id:
        if request.productionBudget is not None or request.qualifyingBudget is not None:
            logger.warning(
                "compare: production_id=%s provided; ignoring manually-passed "
                "productionBudget/qualifyingBudget in favor of live expense totals.",
                request.production_id,
            )
        production = await prisma.production.find_unique(where={"id": request.production_id})
        if not production:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production not found"
            )
        expenses = await prisma.expense.find_many(where={"productionId": request.production_id})
        if not expenses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Production has no expenses to compare. Add or import expenses first."
            )
        production_budget = sum(e.amount for e in expenses)
        qualifying_budget = sum(e.amount for e in expenses if e.isQualifying)
    else:
        production_budget = request.productionBudget
        qualifying_budget = request.qualifyingBudget if request.qualifyingBudget else request.productionBudget

    # Calculate for each jurisdiction (use best rule for each)
    comparisons = []
    
    for jurisdiction in jurisdictions:
        # Get all active rules for this jurisdiction
        rules = await prisma.incentiverule.find_many(
            where={
                "jurisdictionId": jurisdiction.id,
                "active": True
            }
        )
        
        if not rules:
            # No active rules - add with zero credit
            comparisons.append({
                "jurisdiction": jurisdiction.name,
                "jurisdictionId": jurisdiction.id,
                "ruleName": "No active programs",
                "ruleCode": "NONE",
                "incentiveType": "none",
                "percentage": None,
                "estimatedCredit": 0,
                "meetsRequirements": False
            })
            continue
        
        # Calculate credit for each rule, take the best one
        best_credit = 0
        best_rule = rules[0]
        meets_requirements = False
        
        for rule in rules:
            # Calculate credit
            if rule.percentage:
                credit = qualifying_budget * (rule.percentage / 100)
            elif rule.fixedAmount:
                credit = rule.fixedAmount
            else:
                credit = 0
            
            # Check minimum
            meets_min = True
            if rule.minSpend:
                meets_min = qualifying_budget >= rule.minSpend
                if not meets_min:
                    credit = 0
            
            # Apply cap
            if rule.maxCredit and credit > rule.maxCredit:
                credit = rule.maxCredit
            
            # Track best
            if credit > best_credit:
                best_credit = credit
                best_rule = rule
                meets_requirements = meets_min
        
        comparisons.append({
            "jurisdiction": jurisdiction.name,
            "jurisdictionId": jurisdiction.id,
            "ruleName": best_rule.ruleName,
            "ruleCode": best_rule.ruleCode,
            "incentiveType": best_rule.incentiveType,
            "percentage": best_rule.percentage,
            "estimatedCredit": best_credit,
            "meetsRequirements": meets_requirements
        })
    
    # Sort by estimated credit (descending)
    comparisons.sort(key=lambda x: x["estimatedCredit"], reverse=True)
    
    # Add rank and calculate savings
    for i, comp in enumerate(comparisons):
        comp["rank"] = i + 1
        comp["savings"] = comp["estimatedCredit"]
    
    # Best and worst
    best = comparisons[0]
    worst = comparisons[-1]
    savings_vs_worst = best["estimatedCredit"] - worst["estimatedCredit"]
    
    # Convert to Pydantic models
    comparison_results = [ComparisonResult(**comp) for comp in comparisons]
    best_result = ComparisonResult(**best)
    
    # Generate notes
    notes = []
    notes.append(f"ðŸ† Best option: {best['jurisdiction']} with ${best['estimatedCredit']:,.0f} credit")
    notes.append(f"ðŸ’° Saves ${savings_vs_worst:,.0f} vs lowest option ({worst['jurisdiction']})")
    
    if best["percentage"]:
        notes.append(f"ðŸ“Š Top rate: {best['percentage']}% ({best['ruleName']})")
    
    return CompareCalculateResponse(
        totalBudget=production_budget,
        comparisons=comparison_results,
        bestOption=best_result,
        savingsVsWorst=savings_vs_worst,
        notes=notes
    )


@router.get("/jurisdiction/{jurisdiction_id}", summary="Get all rules for a jurisdiction with budget estimate")
async def calculate_jurisdiction_options(
    jurisdiction_id: str,
    budget: float
):
    """
    Get all available incentive rules for a jurisdiction with estimated credits.
    
    Useful for seeing all options in one place.
    """
    
    # Get jurisdiction
    jurisdiction = await prisma.jurisdiction.find_unique(
        where={"id": jurisdiction_id}
    )
    
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jurisdiction not found"
        )
    
    # Get all rules
    rules = await prisma.incentiverule.find_many(
        where={
            "jurisdictionId": jurisdiction_id,
            "active": True
        }
    )
    
    if not rules:
        return {
            "jurisdiction": jurisdiction.name,
            "jurisdictionId": jurisdiction_id,
            "budget": budget,
            "options": [],
            "message": "No active incentive programs available"
        }
    
    # Calculate for each rule
    options = []
    for rule in rules:
        # Calculate
        if rule.percentage:
            credit = budget * (rule.percentage / 100)
        elif rule.fixedAmount:
            credit = rule.fixedAmount
        else:
            credit = 0
        
        # Check requirements
        meets_min = True
        if rule.minSpend:
            meets_min = budget >= rule.minSpend
            if not meets_min:
                credit = 0
        
        if rule.maxCredit and credit > rule.maxCredit:
            credit = rule.maxCredit
        
        options.append({
            "ruleName": rule.ruleName,
            "ruleCode": rule.ruleCode,
            "ruleId": rule.id,
            "incentiveType": rule.incentiveType,
            "percentage": rule.percentage,
            "estimatedCredit": credit,
            "meetsMinimum": meets_min,
            "minimumRequired": rule.minSpend,
            "maximumCap": rule.maxCredit
        })
    
    # Sort by credit amount
    options.sort(key=lambda x: x["estimatedCredit"], reverse=True)
    
    return {
        "jurisdiction": jurisdiction.name,
        "jurisdictionId": jurisdiction_id,
        "budget": budget,
        "options": options,
        "bestOption": options[0] if options else None
    }


@router.post("/compliance", response_model=ComplianceCheckResponse, summary="Check compliance with incentive requirements")
async def check_compliance(request: ComplianceCheckRequest):
    """
    Verify if a production meets all requirements for a specific incentive rule.
    
    Checks:
    - Minimum spend requirements
    - Shoot days requirements
    - Local hiring percentages
    - Special requirements (logos, cultural tests, etc.)
    
    Returns detailed compliance status with action items.
    """
    
    # Get rule
    rule = await prisma.incentiverule.find_unique(
        where={"id": request.ruleId}
    )
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incentive rule not found"
        )
    
    # Get jurisdiction
    jurisdiction = await prisma.jurisdiction.find_unique(
        where={"id": rule.jurisdictionId}
    )
    
    # Get production if ID provided
    production = None
    if request.productionId:
        production = await prisma.production.find_unique(
            where={"id": request.productionId}
        )
        if not production:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production not found"
            )
    
    # Determine budget (from production or request)
    budget = None
    if production:
        budget = production.budgetTotal
    elif request.productionBudget:
        budget = request.productionBudget
    
    qualifying_budget = request.qualifyingBudget or budget
    
    # Parse requirements from rule
    requirements_data = parse_json_field(rule.requirements)
    
    # Track all requirement checks
    requirement_checks = []
    requirements_met = 0
    requirements_not_met = 0
    requirements_unknown = 0
    action_items = []
    warnings = []
    next_steps = []
    
    # Check 1: Minimum Spend
    if rule.minSpend:
        if budget and budget >= rule.minSpend:
            requirement_checks.append(RequirementCheck(
                requirement="minimum_spend",
                description=f"Minimum spend of ${rule.minSpend:,.0f}",
                status="met",
                required=True,
                userValue=budget,
                requiredValue=rule.minSpend,
                notes=f"Budget of ${budget:,.0f} exceeds minimum"
            ))
            requirements_met += 1
        elif budget:
            requirement_checks.append(RequirementCheck(
                requirement="minimum_spend",
                description=f"Minimum spend of ${rule.minSpend:,.0f}",
                status="not_met",
                required=True,
                userValue=budget,
                requiredValue=rule.minSpend,
                notes=f"Budget of ${budget:,.0f} is below minimum"
            ))
            requirements_not_met += 1
            action_items.append(f"âŒ Increase budget to at least ${rule.minSpend:,.0f}")
        else:
            requirement_checks.append(RequirementCheck(
                requirement="minimum_spend",
                description=f"Minimum spend of ${rule.minSpend:,.0f}",
                status="unknown",
                required=True,
                requiredValue=rule.minSpend,
                notes="Budget not provided"
            ))
            requirements_unknown += 1
            action_items.append("âš ï¸ Provide production budget for verification")
    
    # Check 2: Shoot Days (if in requirements)
    if "minShootDays" in requirements_data:
        min_days = requirements_data["minShootDays"]
        if request.shootDays and request.shootDays >= min_days:
            requirement_checks.append(RequirementCheck(
                requirement="minimum_shoot_days",
                description=f"Minimum {min_days} shoot days required",
                status="met",
                required=True,
                userValue=request.shootDays,
                requiredValue=min_days,
                notes=f"{request.shootDays} days scheduled"
            ))
            requirements_met += 1
        elif request.shootDays:
            requirement_checks.append(RequirementCheck(
                requirement="minimum_shoot_days",
                description=f"Minimum {min_days} shoot days required",
                status="not_met",
                required=True,
                userValue=request.shootDays,
                requiredValue=min_days,
                notes=f"Only {request.shootDays} days planned"
            ))
            requirements_not_met += 1
            action_items.append(f"âŒ Extend shoot schedule to at least {min_days} days")
        else:
            requirement_checks.append(RequirementCheck(
                requirement="minimum_shoot_days",
                description=f"Minimum {min_days} shoot days required",
                status="unknown",
                required=True,
                requiredValue=min_days,
                notes="Shoot days not provided"
            ))
            requirements_unknown += 1
            action_items.append("âš ï¸ Provide shoot schedule for verification")
    
    # Check 3: Local Hiring Percentage
    local_hire_keys = ["californiaResidents", "georgiaResident", "localHirePercentage", 
                       "nySpend", "bcResident", "ontarioResident"]
    for key in local_hire_keys:
        if key in requirements_data:
            required_pct = requirements_data[key]
            if request.localHirePercentage is not None:
                if request.localHirePercentage >= required_pct:
                    requirement_checks.append(RequirementCheck(
                        requirement="local_hiring",
                        description=f"Minimum {required_pct}% local hiring required",
                        status="met",
                        required=True,
                        userValue=request.localHirePercentage,
                        requiredValue=required_pct,
                        notes=f"{request.localHirePercentage}% local hiring planned"
                    ))
                    requirements_met += 1
                else:
                    requirement_checks.append(RequirementCheck(
                        requirement="local_hiring",
                        description=f"Minimum {required_pct}% local hiring required",
                        status="not_met",
                        required=True,
                        userValue=request.localHirePercentage,
                        requiredValue=required_pct,
                        notes=f"Only {request.localHirePercentage}% local hiring planned"
                    ))
                    requirements_not_met += 1
                    action_items.append(f"âŒ Increase local hiring to {required_pct}%")
            else:
                requirement_checks.append(RequirementCheck(
                    requirement="local_hiring",
                    description=f"Minimum {required_pct}% local hiring required",
                    status="unknown",
                    required=True,
                    requiredValue=required_pct,
                    notes="Local hiring percentage not provided"
                ))
                requirements_unknown += 1
                action_items.append(f"âš ï¸ Confirm {required_pct}% local hiring commitment")
            break
    
    # Check 4: Promotional Logo
    if "georgiaPromo" in requirements_data or "logoInCredits" in requirements_data:
        if request.hasPromoLogo is True:
            requirement_checks.append(RequirementCheck(
                requirement="promotional_logo",
                description="Include jurisdiction logo in credits",
                status="met",
                required=True,
                userValue=True,
                notes="Logo placement confirmed"
            ))
            requirements_met += 1
        elif request.hasPromoLogo is False:
            requirement_checks.append(RequirementCheck(
                requirement="promotional_logo",
                description="Include jurisdiction logo in credits",
                status="not_met",
                required=True,
                userValue=False,
                notes="Logo not planned for credits"
            ))
            requirements_not_met += 1
            action_items.append(f"âŒ Add {jurisdiction.name} logo to end credits")
        else:
            requirement_checks.append(RequirementCheck(
                requirement="promotional_logo",
                description="Include jurisdiction logo in credits",
                status="unknown",
                required=True,
                notes="Logo placement not confirmed"
            ))
            requirements_unknown += 1
            action_items.append(f"âš ï¸ Confirm {jurisdiction.name} logo placement in credits")
    
    # Check 5: Cultural Test
    if "culturalTest" in requirements_data:
        if request.hasCulturalTest is True:
            requirement_checks.append(RequirementCheck(
                requirement="cultural_test",
                description="Pass cultural test for content",
                status="met",
                required=True,
                userValue=True,
                notes="Cultural test passed"
            ))
            requirements_met += 1
        elif request.hasCulturalTest is False:
            requirement_checks.append(RequirementCheck(
                requirement="cultural_test",
                description="Pass cultural test for content",
                status="not_met",
                required=True,
                userValue=False,
                notes="Cultural test not passed"
            ))
            requirements_not_met += 1
            warnings.append("âš ï¸ Cultural test failure may disqualify production")
        else:
            requirement_checks.append(RequirementCheck(
                requirement="cultural_test",
                description="Pass cultural test for content",
                status="unknown",
                required=True,
                notes="Cultural test status unknown"
            ))
            requirements_unknown += 1
            action_items.append("âš ï¸ Submit cultural test application")
    
    # Check 6: Relocating Production
    if "relocatingProject" in requirements_data:
        if request.isRelocating is not None:
            if request.isRelocating == requirements_data["relocatingProject"]:
                requirement_checks.append(RequirementCheck(
                    requirement="relocating_production",
                    description="Relocating production from another jurisdiction",
                    status="met",
                    required=True,
                    userValue=request.isRelocating,
                    requiredValue=requirements_data["relocatingProject"],
                    notes="Relocation status matches requirement"
                ))
                requirements_met += 1
            else:
                requirement_checks.append(RequirementCheck(
                    requirement="relocating_production",
                    description="Relocating production from another jurisdiction",
                    status="not_met",
                    required=True,
                    userValue=request.isRelocating,
                    requiredValue=requirements_data["relocatingProject"],
                    notes="This program requires relocating production"
                ))
                requirements_not_met += 1
                warnings.append("âŒ This program is only for relocating productions")
        else:
            requirement_checks.append(RequirementCheck(
                requirement="relocating_production",
                description="Relocating production from another jurisdiction",
                status="unknown",
                required=True,
                requiredValue=requirements_data["relocatingProject"],
                notes="Relocation status not specified"
            ))
            requirements_unknown += 1
    
    # Calculate estimated credit if compliant
    estimated_credit = None
    if requirements_not_met == 0 and qualifying_budget:
        if rule.percentage:
            estimated_credit = qualifying_budget * (rule.percentage / 100)
            if rule.maxCredit and estimated_credit > rule.maxCredit:
                estimated_credit = rule.maxCredit
    
    # Determine overall compliance status
    total_requirements = len(requirement_checks)
    
    if total_requirements == 0:
        overall_status = "insufficient_data"
        next_steps.append("ðŸ“‹ Provide production details for full compliance check")
    elif requirements_not_met > 0:
        overall_status = "non_compliant"
        next_steps.append("âŒ Address all failed requirements before applying")
        next_steps.append(f"ðŸ“§ Contact {jurisdiction.name} Film Office for guidance")
    elif requirements_unknown > 0:
        overall_status = "partial"
        next_steps.append("âš ï¸ Confirm all unknown requirements")
        next_steps.append("ðŸ“ Gather missing documentation")
    else:
        overall_status = "compliant"
        next_steps.append(f"âœ… Production qualifies for {rule.ruleName}")
        next_steps.append(f"ðŸ’° Estimated credit: ${estimated_credit:,.0f}" if estimated_credit else "")
        next_steps.append(f"ðŸ“‹ Submit application to {jurisdiction.name} Film Office")
        next_steps.append("ðŸ“„ Prepare required documentation")
    
    # Add warnings for close calls
    if budget and rule.minSpend and budget < (rule.minSpend * 1.1):
        warnings.append(f"âš ï¸ Budget is close to minimum threshold (${rule.minSpend:,.0f})")
    
    return ComplianceCheckResponse(
        overallCompliance=overall_status,
        jurisdiction=jurisdiction.name,
        ruleName=rule.ruleName,
        ruleCode=rule.ruleCode,
        totalRequirements=total_requirements,
        requirementsMet=requirements_met,
        requirementsNotMet=requirements_not_met,
        requirementsUnknown=requirements_unknown,
        requirements=requirement_checks,
        estimatedCredit=estimated_credit,
        actionItems=action_items,
        warnings=warnings,
        nextSteps=next_steps
    )



@router.post("/date-based", response_model=DateBasedRulesResponse, summary="Get rules available on specific date")
async def get_date_based_rules(request: DateBasedRulesRequest):
    """
    Get all incentive rules available for a specific production date.
    
    Useful for:
    - Planning productions months/years in advance
    - Checking if rules have changed
    - Seeing upcoming rule changes
    - Understanding expired programs
    """
    
    # Get jurisdiction
    jurisdiction = await prisma.jurisdiction.find_unique(
        where={"id": request.jurisdictionId}
    )
    
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jurisdiction not found"
        )
    
    # Get all rules for jurisdiction
    all_rules = await prisma.incentiverule.find_many(
        where={"jurisdictionId": request.jurisdictionId}
    )
    
    active_rules = []
    upcoming_rules = []
    expired_rules = []
    
    from datetime import datetime, timedelta
    
    for rule in all_rules:
        effective = rule.effectiveDate.date() if isinstance(rule.effectiveDate, datetime) else rule.effectiveDate
        expiration = rule.expirationDate.date() if rule.expirationDate and isinstance(rule.expirationDate, datetime) else rule.expirationDate
        
        rule_data = {
            "id": rule.id,
            "ruleName": rule.ruleName,
            "ruleCode": rule.ruleCode,
            "percentage": rule.percentage,
            "incentiveType": rule.incentiveType,
            "effectiveDate": effective.isoformat(),
            "expirationDate": expiration.isoformat() if expiration else None
        }
        
        # Check if active on query date
        if effective <= request.productionDate:
            if expiration is None or expiration >= request.productionDate:
                # Active on query date
                active_rules.append(rule_data)
            elif request.includeExpired and (request.productionDate - expiration).days <= 365:
                # Expired within last year
                expired_rules.append(rule_data)
        elif (effective - request.productionDate).days <= 180:
            # Becoming active within 6 months
            upcoming_rules.append(rule_data)
    
    # Generate notes
    notes = []
    if len(active_rules) > 0:
        notes.append(f"âœ… {len(active_rules)} program(s) available on {request.productionDate}")
    else:
        notes.append(f"âš ï¸ No programs available on {request.productionDate}")
    
    if len(upcoming_rules) > 0:
        notes.append(f"ðŸ“… {len(upcoming_rules)} program(s) launching soon")
    
    if len(expired_rules) > 0:
        notes.append(f"â±ï¸ {len(expired_rules)} program(s) recently expired")
    
    return DateBasedRulesResponse(
        jurisdiction=jurisdiction.name,
        queryDate=request.productionDate,
        activeRules=active_rules,
        upcomingRules=upcoming_rules,
        expiredRules=expired_rules,
        totalActive=len(active_rules),
        totalUpcoming=len(upcoming_rules),
        totalExpired=len(expired_rules),
        notes=notes
    )


@router.post("/scenario", response_model=ScenarioCalculateResponse, summary="Model multiple scenarios")
async def calculate_scenarios(request: ScenarioCalculateRequest):
    """
    Model multiple "what if" scenarios for production planning.
    
    Examples:
    - What if we increase budget from $5M to $7M?
    - What if we film in Q1 vs Q4?
    - What if we hire 60% vs 80% local crew?
    - What if we split production between two dates?
    
    Returns comparison of all scenarios with recommendations.
    """
    
    # Get jurisdiction
    jurisdiction = await prisma.jurisdiction.find_unique(
        where={"id": request.jurisdictionId}
    )
    
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jurisdiction not found"
        )
    
    # Get all rules for jurisdiction
    all_rules = await prisma.incentiverule.find_many(
        where={"jurisdictionId": request.jurisdictionId}
    )
    
    from datetime import datetime
    
    # Filter rules by date if provided
    available_rules = []
    expired_count = 0
    
    for rule in all_rules:
        if request.productionStartDate:
            effective = rule.effectiveDate.date() if isinstance(rule.effectiveDate, datetime) else rule.effectiveDate
            expiration = rule.expirationDate.date() if rule.expirationDate and isinstance(rule.expirationDate, datetime) else rule.expirationDate
            
            # Check if rule is active on production date
            if effective <= request.productionStartDate:
                if expiration is None or expiration >= request.productionStartDate:
                    available_rules.append(rule)
                else:
                    expired_count += 1
            # Include expired if requested
            elif request.includeExpiredRules:
                available_rules.append(rule)
                expired_count += 1
        else:
            # No date filtering
            if rule.active:
                available_rules.append(rule)
    
    if not available_rules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No applicable rules found for the specified date"
        )
    
    # Default scenarios if none provided
    scenarios_to_test = request.scenarios if request.scenarios else [
        {"name": "Base Budget", "budget": request.productionBudget},
        {"name": "+20% Budget", "budget": request.productionBudget * 1.2},
        {"name": "-20% Budget", "budget": request.productionBudget * 0.8}
    ]
    
    # Calculate each scenario
    scenario_results = []
    
    for scenario in scenarios_to_test:
        scenario_name = scenario.get("name", "Unnamed Scenario")
        scenario_budget = scenario.get("budget", request.productionBudget)
        scenario_qualifying = scenario.get("qualifyingBudget", scenario_budget)
        
        # Find best rule for this scenario
        best_credit = 0
        best_rule = None
        meets_reqs = False
        
        for rule in available_rules:
            # Calculate credit
            if rule.percentage:
                credit = scenario_qualifying * (rule.percentage / 100)
            elif rule.fixedAmount:
                credit = rule.fixedAmount
            else:
                credit = 0
            
            # Check minimum
            meets_min = True
            if rule.minSpend and scenario_qualifying < rule.minSpend:
                credit = 0
                meets_min = False
            
            # Apply cap
            if rule.maxCredit and credit > rule.maxCredit:
                credit = rule.maxCredit
            
            # Track best
            if credit > best_credit:
                best_credit = credit
                best_rule = rule
                meets_reqs = meets_min
        
        if best_rule:
            effective = best_rule.effectiveDate.date() if isinstance(best_rule.effectiveDate, datetime) else best_rule.effectiveDate
            expiration = best_rule.expirationDate.date() if best_rule.expirationDate and isinstance(best_rule.expirationDate, datetime) else best_rule.expirationDate
            
            is_expired = False
            if expiration and request.productionStartDate:
                is_expired = expiration < request.productionStartDate
            
            effective_rate = (best_credit / scenario_budget * 100) if scenario_budget > 0 else 0
            
            notes = []
            if best_rule.percentage:
                notes.append(f"ðŸ’° {best_rule.percentage}% rate")
            if best_credit > 0:
                notes.append(f"ðŸ’µ ${best_credit:,.0f} estimated credit")
            if not meets_reqs:
                notes.append("âš ï¸ Does not meet minimum requirements")
            if is_expired:
                notes.append("â±ï¸ Rule expired - included for comparison")
            
            scenario_results.append(ScenarioResult(
                scenarioName=scenario_name,
                scenarioParams=scenario,
                bestRuleName=best_rule.ruleName,
                bestRuleCode=best_rule.ruleCode,
                ruleId=best_rule.id,
                estimatedCredit=best_credit,
                effectiveRate=effective_rate,
                meetsRequirements=meets_reqs,
                isActive=best_rule.active,
                isExpired=is_expired,
                effectiveDate=effective,
                expirationDate=expiration,
                notes=notes
            ))
    
    # Sort by credit amount
    scenario_results.sort(key=lambda x: x.estimatedCredit, reverse=True)
    
    best = scenario_results[0]
    worst = scenario_results[-1]
    savings_diff = best.estimatedCredit - worst.estimatedCredit
    
    # Generate recommendations
    recommendations = []
    recommendations.append(f"ðŸ† Best scenario: {best.scenarioName} with ${best.estimatedCredit:,.0f}")
    
    if savings_diff > 0:
        recommendations.append(f"ðŸ’° Optimization potential: ${savings_diff:,.0f} between best and worst scenario")
    
    if best.estimatedCredit > request.productionBudget * 0.25:
        recommendations.append(f"âœ¨ Excellent credit rate: {best.effectiveRate:.1f}% effective rate")
    
    # Check for date-based opportunities
    if expired_count > 0:
        recommendations.append(f"â±ï¸ {expired_count} expired program(s) - check if renewal is planned")
    
    return ScenarioCalculateResponse(
        jurisdiction=jurisdiction.name,
        baseProductionBudget=request.productionBudget,
        productionDate=request.productionStartDate,
        scenarios=scenario_results,
        bestScenario=best,
        worstScenario=worst,
        savingsDifference=savings_diff,
        recommendations=recommendations,
        availableRules=len(available_rules),
        expiredRules=expired_count
    )







