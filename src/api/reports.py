"""
Reports API endpoints - PDF Report Generation
"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from datetime import datetime
import json

from src.models.report import (
    GenerateComparisonReportRequest,
    GenerateComplianceReportRequest,
    GenerateScenarioReportRequest,
    ReportResponse
)
from src.utils.database import prisma
from src.utils.pdf_generator import pdf_generator

router = APIRouter(prefix="/reports", tags=["Reports"])


def parse_json_field(field):
    """Parse JSON field that might be string or dict"""
    if isinstance(field, str):
        return json.loads(field)
    return field if field else {}


@router.post("/comparison", summary="Generate jurisdiction comparison PDF report")
async def generate_comparison_report(request: GenerateComparisonReportRequest):
    """
    Generate a professional PDF report comparing tax incentives across multiple jurisdictions.
    
    Returns a downloadable PDF with:
    - Executive summary
    - Jurisdiction comparison table
    - Detailed analysis
    - Recommendations
    """
    
    # Get jurisdictions
    jurisdictions = await prisma.jurisdiction.find_many(
        where={"id": {"in": request.jurisdictionIds}}
    )
    
    if len(jurisdictions) != len(request.jurisdictionIds):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more jurisdictions not found"
        )
    
    # Calculate for each jurisdiction (reuse comparison logic)
    comparisons = []
    
    for jurisdiction in jurisdictions:
        # Get best rule for this jurisdiction
        rules = await prisma.incentiverule.find_many(
            where={
                "jurisdictionId": jurisdiction.id,
                "active": True
            }
        )
        
        if not rules:
            continue
        
        best_credit = 0
        best_rule = None
        
        for rule in rules:
            if rule.percentage:
                credit = request.budget * (rule.percentage / 100)
            elif rule.fixedAmount:
                credit = rule.fixedAmount
            else:
                credit = 0
            
            if rule.minSpend and request.budget < rule.minSpend:
                credit = 0
            
            if rule.maxCredit and credit > rule.maxCredit:
                credit = rule.maxCredit
            
            if credit > best_credit:
                best_credit = credit
                best_rule = rule
        
        if best_rule:
            comparisons.append({
                "jurisdiction": jurisdiction.name,
                "jurisdictionId": jurisdiction.id,
                "ruleName": best_rule.ruleName,
                "ruleCode": best_rule.ruleCode,
                "incentiveType": best_rule.incentiveType,
                "percentage": best_rule.percentage,
                "estimatedCredit": best_credit,
                "rank": 0  # Will be set after sorting
            })
    
    # Sort by credit amount
    comparisons.sort(key=lambda x: x["estimatedCredit"], reverse=True)
    
    # Add ranks
    for i, comp in enumerate(comparisons):
        comp["rank"] = i + 1
    
    if not comparisons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No applicable incentive programs found"
        )
    
    best_option = comparisons[0]
    
    # Generate PDF
    pdf_bytes = pdf_generator.generate_comparison_report(
        production_title=request.productionTitle,
        budget=request.budget,
        comparisons=comparisons,
        best_option=best_option
    )
    
    # Create filename
    filename = f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Return PDF as download
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/compliance", summary="Generate compliance verification PDF report")
async def generate_compliance_report(request: GenerateComplianceReportRequest):
    """
    Generate a professional PDF report verifying production compliance with incentive requirements.
    
    Returns a downloadable PDF with:
    - Compliance status
    - Requirements checklist
    - Detailed verification
    - Action items
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
    
    # Parse requirements
    requirements_data = parse_json_field(rule.requirements)
    
    # Check requirements (simplified from compliance endpoint)
    requirement_checks = []
    requirements_met = 0
    requirements_not_met = 0
    
    # Minimum spend
    if rule.minSpend:
        if request.productionBudget >= rule.minSpend:
            requirement_checks.append({
                "requirement": "minimum_spend",
                "description": f"Minimum spend of ${rule.minSpend:,.0f}",
                "status": "met"
            })
            requirements_met += 1
        else:
            requirement_checks.append({
                "requirement": "minimum_spend",
                "description": f"Minimum spend of ${rule.minSpend:,.0f}",
                "status": "not_met"
            })
            requirements_not_met += 1
    
    # Shoot days
    if "minShootDays" in requirements_data and request.shootDays:
        min_days = requirements_data["minShootDays"]
        if request.shootDays >= min_days:
            requirement_checks.append({
                "requirement": "shoot_days",
                "description": f"Minimum {min_days} shoot days",
                "status": "met"
            })
            requirements_met += 1
        else:
            requirement_checks.append({
                "requirement": "shoot_days",
                "description": f"Minimum {min_days} shoot days",
                "status": "not_met"
            })
            requirements_not_met += 1
    
    # Local hiring
    local_hire_keys = ["californiaResidents", "georgiaResident", "localHirePercentage"]
    for key in local_hire_keys:
        if key in requirements_data and request.localHirePercentage is not None:
            required_pct = requirements_data[key]
            if request.localHirePercentage >= required_pct:
                requirement_checks.append({
                    "requirement": "local_hiring",
                    "description": f"Minimum {required_pct}% local hiring",
                    "status": "met"
                })
                requirements_met += 1
            else:
                requirement_checks.append({
                    "requirement": "local_hiring",
                    "description": f"Minimum {required_pct}% local hiring",
                    "status": "not_met"
                })
                requirements_not_met += 1
            break
    
    # Promo logo
    if "georgiaPromo" in requirements_data or "logoInCredits" in requirements_data:
        if request.hasPromoLogo:
            requirement_checks.append({
                "requirement": "promotional_logo",
                "description": "Include jurisdiction logo in credits",
                "status": "met"
            })
            requirements_met += 1
        else:
            requirement_checks.append({
                "requirement": "promotional_logo",
                "description": "Include jurisdiction logo in credits",
                "status": "not_met"
            })
            requirements_not_met += 1
    
    # Cultural test
    if "culturalTest" in requirements_data:
        if request.hasCulturalTest:
            requirement_checks.append({
                "requirement": "cultural_test",
                "description": "Pass cultural test for content",
                "status": "met"
            })
            requirements_met += 1
        else:
            requirement_checks.append({
                "requirement": "cultural_test",
                "description": "Pass cultural test for content",
                "status": "not_met"
            })
            requirements_not_met += 1
    
    # Determine overall status
    overall_status = "compliant" if requirements_not_met == 0 else "non_compliant"
    
    # Calculate estimated credit if compliant
    estimated_credit = None
    if overall_status == "compliant":
        if rule.percentage:
            estimated_credit = request.productionBudget * (rule.percentage / 100)
            if rule.maxCredit and estimated_credit > rule.maxCredit:
                estimated_credit = rule.maxCredit
    
    # Generate PDF
    pdf_bytes = pdf_generator.generate_compliance_report(
        production_title=request.productionTitle,
        jurisdiction=jurisdiction.name,
        rule_name=rule.ruleName,
        requirements=requirement_checks,
        overall_status=overall_status,
        estimated_credit=estimated_credit
    )
    
    # Create filename
    filename = f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Return PDF as download
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/scenario", summary="Generate scenario analysis PDF report")
async def generate_scenario_report(request: GenerateScenarioReportRequest):
    """
    Generate a professional PDF report analyzing multiple production scenarios.
    
    Returns a downloadable PDF with:
    - Scenario comparison
    - Optimization analysis
    - ROI calculations
    - Recommendations
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
    
    # Get available rules
    rules = await prisma.incentiverule.find_many(
        where={
            "jurisdictionId": request.jurisdictionId,
            "active": True
        }
    )
    
    if not rules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active incentive rules found"
        )
    
    # Calculate each scenario
    scenario_results = []
    
    for scenario in request.scenarios:
        scenario_name = scenario.get("name", "Unnamed Scenario")
        scenario_budget = scenario.get("budget", request.baseProductionBudget)
        
        # Find best rule
        best_credit = 0
        best_rule = None
        
        for rule in rules:
            if rule.percentage:
                credit = scenario_budget * (rule.percentage / 100)
            elif rule.fixedAmount:
                credit = rule.fixedAmount
            else:
                credit = 0
            
            if rule.minSpend and scenario_budget < rule.minSpend:
                credit = 0
            
            if rule.maxCredit and credit > rule.maxCredit:
                credit = rule.maxCredit
            
            if credit > best_credit:
                best_credit = credit
                best_rule = rule
        
        if best_rule:
            effective_rate = (best_credit / scenario_budget * 100) if scenario_budget > 0 else 0
            
            scenario_results.append({
                "scenarioName": scenario_name,
                "scenarioParams": scenario,
                "bestRuleName": best_rule.ruleName,
                "bestRuleCode": best_rule.ruleCode,
                "estimatedCredit": best_credit,
                "effectiveRate": effective_rate
            })
    
    # Sort by credit amount
    scenario_results.sort(key=lambda x: x["estimatedCredit"], reverse=True)
    
    if not scenario_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No applicable scenarios found"
        )
    
    best_scenario = scenario_results[0]
    
    # Generate PDF
    pdf_bytes = pdf_generator.generate_scenario_report(
        production_title=request.productionTitle,
        jurisdiction=jurisdiction.name,
        base_budget=request.baseProductionBudget,
        scenarios=scenario_results,
        best_scenario=best_scenario
    )
    
    # Create filename
    filename = f"scenario_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Return PDF as download
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
