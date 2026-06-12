"""
Pending Rules API â€” review, approve, and reject Claude-extracted sub-jurisdiction rules.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pending-rules", tags=["Pending Rules"])


class ReviewRequest(BaseModel):
    reviewNotes: Optional[str] = None
    reviewedBy: Optional[str] = None


# â”€â”€ List â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("", summary="List pending rules")
async def list_pending_rules(
    status: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
):
    where = {}
    if status:
        where["status"] = status

    rules = await prisma.pendingrule.find_many(
        where=where,
        include={"jurisdiction": True},
        order={"createdAt": "desc"},
        take=limit,
        skip=skip,
    )
    total = await prisma.pendingrule.count(where=where)
    pending_count = await prisma.pendingrule.count(where={"status": "pending"})

    return {
        "total": total,
        "pendingCount": pending_count,
        "rules": [_serialize(r) for r in rules],
    }


# â”€â”€ Single â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{rule_id}", summary="Get pending rule detail")
async def get_pending_rule(rule_id: str):
    rule = await prisma.pendingrule.find_unique(
        where={"id": rule_id},
        include={"jurisdiction": True},
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Pending rule not found")
    return _serialize(rule)


# â”€â”€ Approve â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{rule_id}/approve", summary="Approve pending rule")
async def approve_rule(rule_id: str, body: ReviewRequest = ReviewRequest()):
    rule = await prisma.pendingrule.find_unique(where={"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Pending rule not found")
    if rule.status != "pending":
        raise HTTPException(status_code=400, detail=f"Rule is already {rule.status}")

    now = datetime.now(timezone.utc)

    updated = await prisma.pendingrule.update(
        where={"id": rule_id},
        data={
            "status": "approved",
            "reviewNotes": body.reviewNotes,
            "reviewedBy": body.reviewedBy,
            "reviewedAt": now,
            "updatedAt": now,
        },
        include={"jurisdiction": True},
    )

    # Promote extracted rules into local_rules
    import json
    extracted = rule.extractedData
    if isinstance(extracted, str):
        extracted = json.loads(extracted)

    promoted = 0
    for i, r in enumerate(extracted.get("rules", [])):
        effective_raw = r.get("effective_date")
        effective_dt = datetime.now(timezone.utc)
        if effective_raw:
            try:
                effective_dt = datetime.strptime(effective_raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        expiry_dt = None
        expiry_raw = r.get("expiration_date")
        if expiry_raw:
            try:
                expiry_dt = datetime.strptime(expiry_raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        code = f"{rule.jurisdictionId[:8].upper()}-AUTO-{rule_id[:6].upper()}-{i+1:02d}"

        try:
            await prisma.localrule.create(data={
                "jurisdiction": {"connect": {"id": rule.jurisdictionId}},
                "name":          r.get("name", "Unnamed Rule"),
                "code":          code,
                "category":      r.get("category", "other"),
                "ruleType":      r.get("rule_type", "requirement"),
                "amount":        r.get("amount"),
                "percentage":    r.get("percentage"),
                "description":   r.get("description", ""),
                "requirements":  r.get("requirements"),
                "effectiveDate": effective_dt,
                "expirationDate": expiry_dt,
                "sourceUrl":     rule.sourceUrl,
                "extractedBy":   "claude",
                "active":        True,
                "updatedAt":     now,
            })
            promoted += 1
        except Exception as e:
            logger.warning(f"Could not promote rule {i+1}: {e}")

    logger.info(f"Approved pending rule {rule_id} â€” promoted {promoted} local rule(s)")
    return {**_serialize(updated), "promotedRules": promoted}


# â”€â”€ Reject â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{rule_id}/reject", summary="Reject pending rule")
async def reject_rule(rule_id: str, body: ReviewRequest = ReviewRequest()):
    rule = await prisma.pendingrule.find_unique(where={"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Pending rule not found")
    if rule.status != "pending":
        raise HTTPException(status_code=400, detail=f"Rule is already {rule.status}")

    now = datetime.now(timezone.utc)
    updated = await prisma.pendingrule.update(
        where={"id": rule_id},
        data={
            "status": "rejected",
            "reviewNotes": body.reviewNotes,
            "reviewedBy": body.reviewedBy,
            "reviewedAt": now,
            "updatedAt": now,
        },
        include={"jurisdiction": True},
    )
    return _serialize(updated)


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _serialize(r) -> dict:
    import json
    extracted = r.extractedData
    if isinstance(extracted, str):
        try:
            extracted = json.loads(extracted)
        except Exception:
            pass
    return {
        "id":             r.id,
        "jurisdictionId": r.jurisdictionId,
        "jurisdiction":   {"id": r.jurisdiction.id, "name": r.jurisdiction.name, "code": r.jurisdiction.code} if r.jurisdiction else None,
        "sourceUrl":      r.sourceUrl,
        "extractedData":  extracted,
        "confidence":     r.confidence,
        "status":         r.status,
        "reviewNotes":    r.reviewNotes,
        "reviewedBy":     r.reviewedBy,
        "reviewedAt":     r.reviewedAt.isoformat() if r.reviewedAt else None,
        "createdAt":      r.createdAt.isoformat() if r.createdAt else None,
        "updatedAt":      r.updatedAt.isoformat() if r.updatedAt else None,
    }


