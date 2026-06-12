"""
Incentive Rule API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
import json
import math

from src.models.incentive_rule import (
    IncentiveRuleCreate,
    IncentiveRuleUpdate,
    IncentiveRuleResponse,
    IncentiveRuleList
)
from src.utils.database import prisma

router = APIRouter(prefix="/incentive-rules", tags=["Incentive Rules"])


@router.get("", response_model=IncentiveRuleList, summary="Get all incentive rules")
async def get_incentive_rules(
    jurisdiction_id: Optional[str] = None,
    incentive_type: Optional[str] = None,
    active:  Optional[bool] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """Retrieve all incentive rules with optional filtering and pagination."""
    where = {}
    if jurisdiction_id:
        where["jurisdictionId"] = jurisdiction_id
    if incentive_type:
        where["incentiveType"] = {"equals": incentive_type, "mode": "insensitive"}
    if active is not None:
        where["active"] = active
    
    # Get total count
    total = await prisma.incentiverule.count(where=where if where else None)
    
    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    
    # Get paginated rules
    rules = await prisma. incentiverule.find_many(
        where=where if where else None,
        order={"ruleName": "asc"},
        skip=skip,
        take=page_size
    )
    
    return {
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "rules": rules
    }


@router.get("/{rule_id}", response_model=IncentiveRuleResponse, summary="Get incentive rule by ID")
async def get_incentive_rule(rule_id: str):
    """Retrieve a specific incentive rule by ID."""
    rule = await prisma.incentiverule.find_unique(
        where={"id": rule_id}
    )
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incentive rule with ID {rule_id} not found"
        )
    
    return rule

