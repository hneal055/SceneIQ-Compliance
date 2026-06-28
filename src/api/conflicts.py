"""
Conflicts API -- list detected rule conflicts and record resolutions/overrides.

GET  /conflicts              -- list conflicts (filter by project, resolved status, type)
GET  /conflicts/{id}         -- get single conflict with its overrides
POST /conflicts/{id}/resolve -- apply a resolution strategy
POST /conflicts/{id}/override -- record a manual user override
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conflicts", tags=["Conflicts"])


# -- Models -------------------------------------------------------------------

class ResolveRequest(BaseModel):
    strategy_name: str          # strictest | most_generous | jurisdiction_priority | user_decides
    resolved_by: Optional[str] = "system"
    notes: Optional[str] = None


class OverrideRequest(BaseModel):
    chosen_rule_key: str
    chosen_value: Optional[float] = None
    chosen_by: Optional[str] = None  # user id (UUID string)
    notes: Optional[str] = None


# -- Endpoints ----------------------------------------------------------------

@router.get("", summary="List detected conflicts")
async def list_conflicts(
    project_id: Optional[str] = None,
    conflict_type: Optional[str] = None,
    unresolved_only: bool = True,
    limit: int = 100,
    skip: int = 0,
):
    where: dict = {}

    if project_id:
        where["projectId"] = project_id

    if conflict_type:
        where["conflictType"] = conflict_type

    if unresolved_only:
        where["resolvedAt"] = None

    conflicts = await prisma.detectedconflict.find_many(
        where=where,
        include={
            "jurisdiction": True,
            "resolutionStrategy": True,
            "userOverrides": True,
        },
        order={"createdAt": "desc"},
        take=limit,
        skip=skip,
    )

    total = await prisma.detectedconflict.count(where=where)

    return {"total": total, "conflicts": conflicts}


@router.get("/{conflict_id}", summary="Get a single conflict with overrides")
async def get_conflict(conflict_id: str):
    conflict = await prisma.detectedconflict.find_unique(
        where={"id": conflict_id},
        include={
            "jurisdiction": True,
            "resolutionStrategy": True,
            "userOverrides": True,
        },
    )
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return conflict


@router.post("/{conflict_id}/resolve", summary="Apply a resolution strategy to a conflict")
async def resolve_conflict(conflict_id: str, body: ResolveRequest):
    conflict = await prisma.detectedconflict.find_unique(where={"id": conflict_id})
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    strategy = await prisma.conflictresolutionstrategy.find_unique(
        where={"strategyName": body.strategy_name}
    )
    if not strategy:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown strategy '{body.strategy_name}'. "
                "Valid options: strictest, most_generous, jurisdiction_priority, user_decides"
            ),
        )

    # Compute resolved_value based on strategy
    resolved_value: Optional[float] = None
    if strategy.strategyName == "strictest":
        if conflict.value1 is not None and conflict.value2 is not None:
            resolved_value = float(min(float(conflict.value1), float(conflict.value2)))
    elif strategy.strategyName == "most_generous":
        if conflict.value1 is not None and conflict.value2 is not None:
            resolved_value = float(max(float(conflict.value1), float(conflict.value2)))
    elif strategy.strategyName == "jurisdiction_priority":
        # value1 belongs to the higher-level jurisdiction (state/county) by convention
        resolved_value = float(conflict.value1) if conflict.value1 is not None else None

    now = datetime.now(timezone.utc)

    updated = await prisma.detectedconflict.update(
        where={"id": conflict_id},
        data={
            "resolutionStrategyId": strategy.id,
            "resolvedValue": resolved_value,
            "resolvedBy": body.resolved_by or "system",
            "resolvedAt": now,
            "notes": body.notes,
        },
        include={"resolutionStrategy": True},
    )
    return updated


@router.post("/{conflict_id}/override", summary="Record a manual user override for a conflict")
async def override_conflict(conflict_id: str, body: OverrideRequest):
    conflict = await prisma.detectedconflict.find_unique(where={"id": conflict_id})
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    # Resolve via the user_decides strategy
    strategy = await prisma.conflictresolutionstrategy.find_unique(
        where={"strategyName": "user_decides"}
    )

    now = datetime.now(timezone.utc)

    override = await prisma.userconflictoverride.create(
        data={
            "conflictId": conflict_id,
            "chosenRuleKey": body.chosen_rule_key,
            "chosenValue": body.chosen_value,
            "chosenBy": body.chosen_by,
            "notes": body.notes,
        }
    )

    await prisma.detectedconflict.update(
        where={"id": conflict_id},
        data={
            "resolutionStrategyId": strategy.id if strategy else None,
            "resolvedValue": body.chosen_value,
            "resolvedBy": body.chosen_by or "user",
            "resolvedAt": now,
        },
    )

    return {"override": override, "conflict_id": conflict_id}



