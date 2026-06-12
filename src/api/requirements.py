"""
Compliance checklist â€” Jurisdiction Requirements API
=====================================================
Routes
------
GET  /jurisdictions/{code}/requirements          Checklist for a jurisdiction
POST /jurisdictions/{code}/requirements          Create a requirement manually
PATCH  /requirements/{requirement_id}            Update a requirement
DELETE /requirements/{requirement_id}            Remove a requirement
"""

import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from src.models.requirement import (
    ChecklistItem,
    ChecklistResponse,
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
)
from src.utils.database import prisma

router = APIRouter(tags=["Requirements"])


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _get_jurisdiction_or_404(code: str):
    jur = await prisma.jurisdiction.find_unique(where={"code": code})
    if not jur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Jurisdiction '{code}' not found",
        )
    return jur


def _matches_project_type(applicable_to: list[str], project_type: Optional[str]) -> bool:
    """Return True if the requirement applies to the requested project type.
    An empty applicableTo list means the requirement applies to all types.
    """
    if not project_type:
        return True
    if not applicable_to:
        return True
    return project_type.lower() in [t.lower() for t in applicable_to]


# â”€â”€ GET checklist â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get(
    "/jurisdictions/{code}/requirements",
    response_model=ChecklistResponse,
    summary="Get compliance checklist for a jurisdiction",
)
async def get_requirements(
    code: str,
    project_type: Optional[str] = None,
    include_parent: bool = True,
    active_only: bool = True,
):
    """
    Return the compliance checklist for a jurisdiction.

    - **code**: Jurisdiction code, e.g. `NY-NASSAU`, `NY-NYC`, `CA`
    - **project_type**: Optional filter â€” `film`, `commercial`, `tv_series`, etc.
      Requirements with an empty `applicableTo` list always appear.
    - **include_parent**: Also include requirements from the parent jurisdiction
      (e.g. NY state requirements when querying NY-NASSAU). Default `true`.
    - **active_only**: Exclude inactive requirements. Default `true`.
    """
    jur = await _get_jurisdiction_or_404(code)

    where_base: dict = {"jurisdictionId": jur.id}
    if active_only:
        where_base["active"] = True

    own_reqs = await prisma.jurisdictionrequirement.find_many(
        where=where_base,
        order={"category": "asc"},
    )

    items: list[ChecklistItem] = []

    for r in own_reqs:
        if not _matches_project_type(list(r.applicableTo or []), project_type):
            continue
        items.append(
            ChecklistItem(
                **{
                    "id": r.id,
                    "jurisdictionId": r.jurisdictionId,
                    "name": r.name,
                    "category": r.category,
                    "requirementType": r.requirementType,
                    "description": r.description,
                    "applicableTo": list(r.applicableTo or []),
                    "contactInfo": r.contactInfo,
                    "portalUrl": r.portalUrl,
                    "sourceUrl": r.sourceUrl,
                    "extractedBy": r.extractedBy,
                    "active": r.active,
                    "createdAt": r.createdAt,
                    "updatedAt": r.updatedAt,
                    "fromParent": False,
                }
            )
        )

    # Optionally walk up one level to the parent jurisdiction
    if include_parent and jur.parentId:
        parent = await prisma.jurisdiction.find_unique(where={"id": jur.parentId})
        if parent:
            parent_reqs = await prisma.jurisdictionrequirement.find_many(
                where={
                    "jurisdictionId": parent.id,
                    **({"active": True} if active_only else {}),
                },
                order={"category": "asc"},
            )
            for r in parent_reqs:
                if not _matches_project_type(list(r.applicableTo or []), project_type):
                    continue
                items.append(
                    ChecklistItem(
                        **{
                            "id": r.id,
                            "jurisdictionId": r.jurisdictionId,
                            "name": r.name,
                            "category": r.category,
                            "requirementType": r.requirementType,
                            "description": r.description,
                            "applicableTo": list(r.applicableTo or []),
                            "contactInfo": r.contactInfo,
                            "portalUrl": r.portalUrl,
                            "sourceUrl": r.sourceUrl,
                            "extractedBy": r.extractedBy,
                            "active": r.active,
                            "createdAt": r.createdAt,
                            "updatedAt": r.updatedAt,
                            "fromParent": True,
                            "parentJurisdictionCode": parent.code,
                            "parentJurisdictionName": parent.name,
                        }
                    )
                )

    by_category = dict(Counter(item.category for item in items))

    return ChecklistResponse(
        jurisdictionCode=jur.code,
        jurisdictionName=jur.name,
        projectType=project_type,
        total=len(items),
        byCategory=by_category,
        requirements=items,
    )


# â”€â”€ POST â€” manual create â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post(
    "/jurisdictions/{code}/requirements",
    response_model=RequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually add a requirement to a jurisdiction",
)
async def create_requirement(code: str, body: RequirementCreate):
    """
    Add a non-quantified requirement to a jurisdiction.
    Useful for manually entering Westchester/Erie/Cook permit info
    that isn't yet available via the automated monitor.
    """
    jur = await _get_jurisdiction_or_404(code)

    now = datetime.now(timezone.utc)
    req = await prisma.jurisdictionrequirement.create(
        data={
            "id": str(uuid.uuid4()),
            "jurisdictionId": jur.id,
            "name": body.name,
            "category": body.category,
            "requirementType": body.requirementType,
            "description": body.description,
            "applicableTo": body.applicableTo,
            "contactInfo": body.contactInfo,
            "portalUrl": body.portalUrl,
            "sourceUrl": body.sourceUrl,
            "extractedBy": body.extractedBy,
            "active": body.active,
            "updatedAt": now,
        }
    )
    return req


# â”€â”€ PATCH â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch(
    "/requirements/{requirement_id}",
    response_model=RequirementResponse,
    summary="Update a requirement",
)
async def update_requirement(requirement_id: str, body: RequirementUpdate):
    existing = await prisma.jurisdictionrequirement.find_unique(
        where={"id": requirement_id}
    )
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement '{requirement_id}' not found",
        )

    update_data = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None
    }
    update_data["updatedAt"] = datetime.now(timezone.utc)

    return await prisma.jurisdictionrequirement.update(
        where={"id": requirement_id},
        data=update_data,
    )


# â”€â”€ DELETE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.delete(
    "/requirements/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a requirement",
)
async def delete_requirement(requirement_id: str):
    existing = await prisma.jurisdictionrequirement.find_unique(
        where={"id": requirement_id}
    )
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement '{requirement_id}' not found",
        )
    await prisma.jurisdictionrequirement.delete(where={"id": requirement_id})


