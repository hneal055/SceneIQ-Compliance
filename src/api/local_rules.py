"""
Local Rules API â€” CRUD for county/city/town-level incentive rules.
These are rules that have been approved from pending_rules or entered manually.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/local-rules", tags=["Local Rules"])


# â”€â”€ Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class LocalRuleCreate(BaseModel):
    jurisdictionId: str
    name: str
    code: str
    category: str
    ruleType: str
    amount: Optional[float] = None
    percentage: Optional[float] = None
    description: str
    requirements: Optional[str] = None
    effectiveDate: str
    expirationDate: Optional[str] = None
    sourceUrl: Optional[str] = None


class LocalRuleUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    ruleType: Optional[str] = None
    amount: Optional[float] = None
    percentage: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    effectiveDate: Optional[str] = None
    expirationDate: Optional[str] = None
    sourceUrl: Optional[str] = None
    active: Optional[bool] = None


# â”€â”€ List â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("", summary="List local rules")
async def list_local_rules(
    jurisdiction_id: Optional[str] = None,
    jurisdiction_code: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True,
    limit: int = 100,
    skip: int = 0,
):
    where: dict = {}

    if active_only:
        where["active"] = True

    if jurisdiction_id:
        where["jurisdictionId"] = jurisdiction_id
    elif jurisdiction_code:
        jur = await prisma.jurisdiction.find_unique(where={"code": jurisdiction_code})
        if not jur:
            raise HTTPException(status_code=404, detail=f"Jurisdiction '{jurisdiction_code}' not found")
        where["jurisdictionId"] = jur.id

    if category:
        where["category"] = category

    rules = await prisma.localrule.find_many(
        where=where,
        include={"jurisdiction": True},
        order={"effectiveDate": "desc"},
        take=limit,
        skip=skip,
    )
    total = await prisma.localrule.count(where=where)

    return {
        "total": total,
        "rules": [_serialize(r) for r in rules],
    }


# â”€â”€ By jurisdiction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/by-jurisdiction/{jurisdiction_code}", summary="Get all local rules for a jurisdiction")
async def rules_by_jurisdiction(jurisdiction_code: str, active_only: bool = True):
    jur = await prisma.jurisdiction.find_unique(
        where={"code": jurisdiction_code},
        include={"localRules": True},
    )
    if not jur:
        raise HTTPException(status_code=404, detail=f"Jurisdiction '{jurisdiction_code}' not found")

    rules = jur.localRules or []
    if active_only:
        rules = [r for r in rules if r.active]

    return {
        "jurisdiction": {
            "id": jur.id,
            "name": jur.name,
            "code": jur.code,
            "type": jur.type,
            "parentId": jur.parentId,
        },
        "total": len(rules),
        "rules": [_serialize(r) for r in rules],
    }


# â”€â”€ Single â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{rule_id}", summary="Get local rule detail")
async def get_local_rule(rule_id: str):
    rule = await prisma.localrule.find_unique(
        where={"id": rule_id},
        include={"jurisdiction": True},
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Local rule not found")
    return _serialize(rule)


# â”€â”€ Create â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("", summary="Create local rule manually", status_code=201)
async def create_local_rule(body: LocalRuleCreate):
    jur = await prisma.jurisdiction.find_unique(where={"id": body.jurisdictionId})
    if not jur:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    existing = await prisma.localrule.find_unique(where={"code": body.code})
    if existing:
        raise HTTPException(status_code=409, detail=f"Rule code '{body.code}' already exists")

    now = datetime.now(timezone.utc)
    rule = await prisma.localrule.create(
        data={
            "jurisdiction": {"connect": {"id": body.jurisdictionId}},
            "name": body.name,
            "code": body.code,
            "category": body.category,
            "ruleType": body.ruleType,
            "amount": body.amount,
            "percentage": body.percentage,
            "description": body.description,
            "requirements": body.requirements,
            "effectiveDate": datetime.fromisoformat(body.effectiveDate).replace(tzinfo=timezone.utc),
            "expirationDate": datetime.fromisoformat(body.expirationDate).replace(tzinfo=timezone.utc) if body.expirationDate else None,
            "sourceUrl": body.sourceUrl,
            "extractedBy": "manual",
            "active": True,
            "updatedAt": now,
        },
        include={"jurisdiction": True},
    )
    return _serialize(rule)


# â”€â”€ Update â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{rule_id}", summary="Update local rule")
async def update_local_rule(rule_id: str, body: LocalRuleUpdate):
    rule = await prisma.localrule.find_unique(where={"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Local rule not found")

    data: dict = {"updatedAt": datetime.now(timezone.utc)}
    if body.name is not None:         data["name"] = body.name
    if body.category is not None:     data["category"] = body.category
    if body.ruleType is not None:     data["ruleType"] = body.ruleType
    if body.amount is not None:       data["amount"] = body.amount
    if body.percentage is not None:   data["percentage"] = body.percentage
    if body.description is not None:  data["description"] = body.description
    if body.requirements is not None: data["requirements"] = body.requirements
    if body.sourceUrl is not None:    data["sourceUrl"] = body.sourceUrl
    if body.active is not None:       data["active"] = body.active
    if body.effectiveDate is not None:
        data["effectiveDate"] = datetime.fromisoformat(body.effectiveDate).replace(tzinfo=timezone.utc)
    if body.expirationDate is not None:
        data["expirationDate"] = datetime.fromisoformat(body.expirationDate).replace(tzinfo=timezone.utc)

    updated = await prisma.localrule.update(
        where={"id": rule_id},
        data=data,
        include={"jurisdiction": True},
    )
    return _serialize(updated)


# â”€â”€ Delete (soft) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.delete("/{rule_id}", summary="Deactivate local rule")
async def delete_local_rule(rule_id: str):
    rule = await prisma.localrule.find_unique(where={"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Local rule not found")

    await prisma.localrule.update(
        where={"id": rule_id},
        data={"active": False, "updatedAt": datetime.now(timezone.utc)},
    )
    return {"message": "Local rule deactivated"}


# â”€â”€ Summary stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/stats/summary", summary="Local rules summary stats")
async def local_rules_stats():
    total = await prisma.localrule.count()
    active = await prisma.localrule.count(where={"active": True})
    by_source = await prisma.query_raw(
        'SELECT "extractedBy", COUNT(*) as count FROM local_rules GROUP BY "extractedBy"'
    )
    by_category = await prisma.query_raw(
        'SELECT category, COUNT(*) as count FROM local_rules WHERE active = true GROUP BY category ORDER BY count DESC'
    )
    return {
        "total": total,
        "active": active,
        "bySource": by_source,
        "byCategory": by_category,
    }


# â”€â”€ Helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _serialize(r) -> dict:
    return {
        "id":             r.id,
        "jurisdictionId": r.jurisdictionId,
        "jurisdiction":   {"id": r.jurisdiction.id, "name": r.jurisdiction.name, "code": r.jurisdiction.code, "type": r.jurisdiction.type} if r.jurisdiction else None,
        "name":           r.name,
        "code":           r.code,
        "category":       r.category,
        "ruleType":       r.ruleType,
        "amount":         r.amount,
        "percentage":     r.percentage,
        "description":    r.description,
        "requirements":   r.requirements,
        "effectiveDate":  r.effectiveDate.isoformat() if r.effectiveDate else None,
        "expirationDate": r.expirationDate.isoformat() if r.expirationDate else None,
        "sourceUrl":      r.sourceUrl,
        "extractedBy":    r.extractedBy,
        "active":         r.active,
        "createdAt":      r.createdAt.isoformat() if r.createdAt else None,
        "updatedAt":      r.updatedAt.isoformat() if r.updatedAt else None,
    }

