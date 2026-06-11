"""
Expenses API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional
from collections import defaultdict

from src.models.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseList,
    ExpenseSummary,
    ProductionExpenseCalculation
)
from src.utils.database import prisma
import json

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def parse_json_field(field):
    """Parse JSON field that might be string or dict"""
    if isinstance(field, str):
        return json.loads(field)
    return field if field else {}


@router.get("/", response_model=ExpenseList, summary="Get all expenses")
async def get_expenses(
    production_id: Optional[str] = None,
    category: Optional[str] = None,
    is_qualifying: Optional[bool] = None
):
    """Retrieve all expenses with optional filtering."""
    where = {}
    if production_id:
        where["productionId"] = production_id
    if category:
        where["category"] = {"equals": category, "mode": "insensitive"}
    if is_qualifying is not None:
        where["isQualifying"] = is_qualifying
    
    expenses = await prisma.expense.find_many(
        where=where if where else None,
        order={"expenseDate": "desc"}
    )
    
    # Calculate totals
    total_amount = sum(e.amount for e in expenses)
    qualifying_amount = sum(e.amount for e in expenses if e.isQualifying)
    non_qualifying_amount = sum(e.amount for e in expenses if not e.isQualifying)
    
    return ExpenseList(
        total=len(expenses),
        totalAmount=total_amount,
        qualifyingAmount=qualifying_amount,
        nonQualifyingAmount=non_qualifying_amount,
        expenses=expenses
    )


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Get expense by ID")
async def get_expense(expense_id: str):
    """Retrieve a specific expense by ID."""
    expense = await prisma.expense.find_unique(
        where={"id": expense_id}
    )
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found"
        )
    
    return expense


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED, summary="Create expense")
async def create_expense(expense: ExpenseCreate):
    """Create a new production expense."""
    # Verify production exists
    production = await prisma.production.find_unique(
        where={"id": expense.productionId}
    )
    
    if not production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production with ID {expense.productionId} not found"
        )
    
    new_expense = await prisma.expense.create(
        data=expense.model_dump()
    )
    
    return new_expense


@router.put("/{expense_id}", response_model=ExpenseResponse, summary="Update expense")
async def update_expense(expense_id: str, expense: ExpenseUpdate):
    """Update an existing expense."""
    existing = await prisma.expense.find_unique(
        where={"id": expense_id}
    )
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found"
        )
    
    update_data = expense.model_dump(exclude_unset=True)
    
    updated = await prisma.expense.update(
        where={"id": expense_id},
        data=update_data
    )
    
    return updated


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete expense")
async def delete_expense(expense_id: str):
    """Delete an expense."""
    existing = await prisma.expense.find_unique(
        where={"id": expense_id}
    )
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found"
        )
    
    await prisma.expense.delete(
        where={"id": expense_id}
    )
    
    return None


@router.get("/production/{production_id}/calculate", response_model=ProductionExpenseCalculation, summary="Calculate credit from actual expenses")
async def calculate_from_expenses(production_id: str):
    """
    Calculate tax credit based on actual production expenses.
    
    This is the real-time calculator that updates as expenses are added!
    """
    # Get production
    production = await prisma.production.find_unique(
        where={"id": production_id}
    )
    
    if not production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production with ID {production_id} not found"
        )
    
    # Get jurisdiction
    jurisdiction = await prisma.jurisdiction.find_unique(
        where={"id": production.jurisdictionId}
    )
    
    # Get all expenses for this production
    expenses = await prisma.expense.find_many(
        where={"productionId": production_id}
    )
    
    if not expenses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No expenses found for this production. Add expenses first."
        )
    
    # Calculate totals
    total_expenses = sum(e.amount for e in expenses)
    qualifying_expenses = sum(e.amount for e in expenses if e.isQualifying)
    non_qualifying_expenses = sum(e.amount for e in expenses if not e.isQualifying)
    qualifying_pct = (qualifying_expenses / total_expenses * 100) if total_expenses > 0 else 0
    
    # Summarize by category
    category_summary = defaultdict(lambda: {"total": 0, "qualifying": 0, "non_qualifying": 0, "count": 0})
    
    for expense in expenses:
        cat = expense.category
        category_summary[cat]["total"] += expense.amount
        category_summary[cat]["count"] += 1
        if expense.isQualifying:
            category_summary[cat]["qualifying"] += expense.amount
        else:
            category_summary[cat]["non_qualifying"] += expense.amount
    
    expenses_by_category = [
        ExpenseSummary(
            category=cat,
            totalAmount=data["total"],
            qualifyingAmount=data["qualifying"],
            nonQualifyingAmount=data["non_qualifying"],
            count=data["count"]
        )
        for cat, data in category_summary.items()
    ]
    
    # Sort by total amount
    expenses_by_category.sort(key=lambda x: x.totalAmount, reverse=True)
    
    # Get available rules
    rules = await prisma.incentiverule.find_many(
        where={
            "jurisdictionId": production.jurisdictionId,
            "active": True
        }
    )
    
    if not rules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active incentive rules found for {jurisdiction.name}"
        )
    
    # Find best rule
    best_credit = 0
    best_rule = None
    meets_min = False
    
    for rule in rules:
        # Calculate credit
        if rule.percentage:
            credit = qualifying_expenses * (rule.percentage / 100)
        elif rule.fixedAmount:
            credit = rule.fixedAmount
        else:
            credit = 0
        
        # Check minimum
        meets_minimum = True
        if rule.minSpend and qualifying_expenses < rule.minSpend:
            credit = 0
            meets_minimum = False
        
        # Apply cap
        if rule.maxCredit and credit > rule.maxCredit:
            credit = rule.maxCredit
        
        # Track best
        if credit > best_credit:
            best_credit = credit
            best_rule = rule
            meets_min = meets_minimum
    
    if not best_rule:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not determine applicable rule"
        )
    
    under_max = True
    if best_rule.maxCredit and best_credit >= best_rule.maxCredit:
        under_max = False
    
    # Generate notes and recommendations
    notes = []
    recommendations = []
    
    notes.append(f"ðŸ’° {len(expenses)} expenses totaling ${total_expenses:,.0f}")
    notes.append(f"âœ… Qualifying: ${qualifying_expenses:,.0f} ({qualifying_pct:.1f}%)")
    notes.append(f"âŒ Non-qualifying: ${non_qualifying_expenses:,.0f}")
    if best_rule.percentage:
        notes.append(f"ðŸ“Š Rate: {best_rule.percentage}%")
    
    if not meets_min and best_rule.minSpend:
        shortage = best_rule.minSpend - qualifying_expenses
        notes.append(f"âš ï¸ Below minimum: Need ${shortage:,.0f} more in qualifying expenses")
        recommendations.append(f"Add ${shortage:,.0f} in qualifying expenses to unlock credit")
    
    if not under_max and best_rule.maxCredit:
        notes.append(f"â„¹ï¸ Credit capped at maximum of ${best_rule.maxCredit:,.0f}")
    
    if meets_min and best_credit > 0:
        notes.append(f"ðŸ’µ Estimated credit: ${best_credit:,.0f}")
        recommendations.append(f"Continue tracking expenses - currently at ${best_credit:,.0f} credit")
    
    return ProductionExpenseCalculation(
        productionId=production_id,
        productionTitle=production.title,
        jurisdictionName=jurisdiction.name,
        totalExpenses=total_expenses,
        qualifyingExpenses=qualifying_expenses,
        nonQualifyingExpenses=non_qualifying_expenses,
        qualifyingPercentage=qualifying_pct,
        bestRuleName=best_rule.ruleName,
        bestRuleCode=best_rule.ruleCode,
        ruleId=best_rule.id,
        appliedRate=best_rule.percentage or 0,
        estimatedCredit=best_credit,
        meetsMinimum=meets_min,
        minimumRequired=best_rule.minSpend,
        underMaximum=under_max,
        maximumCap=best_rule.maxCredit,
        expensesByCategory=expenses_by_category,
        totalExpensesCount=len(expenses),
        notes=notes,
        recommendations=recommendations
    )
