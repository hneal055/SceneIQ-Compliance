"""
Jurisdiction API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional
from datetime import datetime
import uuid

from src.models.jurisdiction import (
    JurisdictionCreate,
    JurisdictionUpdate,
    JurisdictionResponse,
    JurisdictionList
)
from src.utils.database import prisma

router = APIRouter(prefix="/jurisdictions", tags=["Jurisdictions"])


@router.get("", response_model=JurisdictionList, summary="Get all jurisdictions")
async def get_jurisdictions(
    country: Optional[str] = None,
    type: Optional[str] = None,
    active: Optional[bool] = None
):
    """
    Retrieve all jurisdictions with optional filtering.
    
    - **country**: Filter by country (e.g., USA, Canada)
    - **type**: Filter by type (state, province, country)
    - **active**: Filter by active status
    """
    where = {}
    if country:
        where["country"] = {"equals": country, "mode": "insensitive"}
    if type:
        where["type"] = {"equals": type, "mode": "insensitive"}
    if active is not None:
        where["active"] = active
    
    jurisdictions = await prisma.jurisdiction.find_many(
        where=where if where else None,
        order={"name": "asc"}
    )
    
    return {
        "total": len(jurisdictions),
        "jurisdictions": jurisdictions
    }


@router.get("/{jurisdiction_id}", response_model=JurisdictionResponse, summary="Get jurisdiction by ID")
async def get_jurisdiction(jurisdiction_id: str):
    """
    Retrieve a specific jurisdiction by ID.
    
    - **jurisdiction_id**: The unique identifier of the jurisdiction
    """
    jurisdiction = await prisma.jurisdiction.find_unique(
        where={"id": jurisdiction_id}
    )
    
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Jurisdiction with ID {jurisdiction_id} not found"
        )
    
    return jurisdiction


@router.post("/", response_model=JurisdictionResponse, status_code=status.HTTP_201_CREATED, summary="Create jurisdiction")
async def create_jurisdiction(jurisdiction: JurisdictionCreate):
    """
    Create a new jurisdiction.
    
    - **name**: Full name of the jurisdiction
    - **code**: Short code (e.g., CA, NY, BC)
    - **country**: Country name
    - **type**: Type of jurisdiction (state, province, country)
    """
    # Check if code already exists
    existing = await prisma.jurisdiction.find_first(
        where={"code": {"equals": jurisdiction.code, "mode": "insensitive"}}
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Jurisdiction with code '{jurisdiction.code}' already exists"
        )
    
    new_jurisdiction = await prisma.jurisdiction.create(
        data=jurisdiction.model_dump()
    )
    
    return new_jurisdiction


@router.put("/{jurisdiction_id}", response_model=JurisdictionResponse, summary="Update jurisdiction")
async def update_jurisdiction(jurisdiction_id: str, jurisdiction: JurisdictionUpdate):
    """
    Update an existing jurisdiction.
    
    - **jurisdiction_id**: The ID of the jurisdiction to update
    - Only provided fields will be updated
    """
    existing = await prisma.jurisdiction.find_unique(
        where={"id": jurisdiction_id}
    )
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Jurisdiction with ID {jurisdiction_id} not found"
        )
    
    update_data = jurisdiction.model_dump(exclude_unset=True)
    
    updated = await prisma.jurisdiction.update(
        where={"id": jurisdiction_id},
        data=update_data
    )
    
    return updated


@router.delete("/{jurisdiction_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete jurisdiction")
async def delete_jurisdiction(jurisdiction_id: str):
    """
    Delete a jurisdiction.
    
    - **jurisdiction_id**: The ID of the jurisdiction to delete
    """
    existing = await prisma.jurisdiction.find_unique(
        where={"id": jurisdiction_id}
    )
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Jurisdiction with ID {jurisdiction_id} not found"
        )
    
    await prisma.jurisdiction.delete(
        where={"id": jurisdiction_id}
    )
    
    return None




