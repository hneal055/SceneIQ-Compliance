"""
Production API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from typing import Optional
import logging
from datetime import datetime

from src.models.production import (
    ProductionCreate,
    ProductionUpdate,
    ProductionResponse,
    ProductionList
)
from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/productions", tags=["Productions"])


def format_datetime(dt):
    """Convert datetime to ISO-8601 with Z suffix"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    return str(dt) + 'Z' if not str(dt).endswith('Z') else str(dt)


@router.get("", response_model=ProductionList, summary="Get all productions")
async def get_productions(
    production_type: Optional[str] = None,
    active: Optional[bool] = None
):
    """Retrieve all productions with optional filtering."""
    logger.info("GET productions called")
    where = {}
    if production_type:
        where["productionType"] = {"equals": production_type, "mode": "insensitive"}
    
    productions = await prisma.production.find_many(
        where=where if where else None,
        order={"createdAt": "desc"}
    )
    
    logger.info(f"Found {len(productions)} productions")
    return {
        "total": len(productions),
        "productions": productions
    }


@router.post("", response_model=ProductionResponse, status_code=status.HTTP_201_CREATED, summary="Create production")
async def create_production(production: ProductionCreate):
    """Create a new production."""
    try:
        logger.info(f"Creating production: {production.title}")
        
        # Verify jurisdiction exists
        jurisdiction = await prisma.jurisdiction.find_unique(
            where={"id": production.jurisdictionId}
        )
        
        if not jurisdiction:
            logger.error(f"Jurisdiction not found: {production.jurisdictionId}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Jurisdiction with ID {production.jurisdictionId} not found"
            )
        
        logger.info(f"Jurisdiction found: {jurisdiction.name}")
        
        # Build data dict - use BOTH jurisdictionId AND relationship
        data = {
            "title": production.title,
            "productionType": production.productionType,
            "jurisdictionId": production.jurisdictionId,  # Required field
            "budgetTotal": production.budgetTotal,
            "budgetQualifying": production.budgetQualifying,
            "startDate": format_datetime(production.startDate),
            "endDate": format_datetime(production.endDate),
            "productionCompany": production.productionCompany,
            "episodeCount": production.episodeCount,
            "status": production.status,
            "contact": production.contact,
            "metadata": production.metadata,
        }
        
        logger.info(f"Data to create: {data}")
        
        # Create production
        new_production = await prisma.production.create(data=data)
        
        logger.info(f"Production created: {new_production.id}")
        return new_production
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating production: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating production: {str(e)}"
        )


@router.get("/{production_id}", response_model=ProductionResponse, summary="Get production by ID")
async def get_production(production_id: str):
    """Retrieve a specific production by ID."""
    production = await prisma.production.find_unique(
        where={"id": production_id}
    )
    
    if not production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production with ID {production_id} not found"
        )
    
    return production


@router.put("/{production_id}", response_model=ProductionResponse, summary="Update production")
async def update_production(production_id: str, production: ProductionUpdate):
    """Update an existing production."""
    existing = await prisma.production.find_unique(
        where={"id": production_id}
    )
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production with ID {production_id} not found"
        )
    
    update_data = {}
    
    if production.title is not None:
        update_data["title"] = production.title
    if production.productionType is not None:
        update_data["productionType"] = production.productionType
    if production.budgetTotal is not None:
        update_data["budgetTotal"] = production.budgetTotal
    if production.budgetQualifying is not None:
        update_data["budgetQualifying"] = production.budgetQualifying
    if production.startDate is not None:
        update_data["startDate"] = format_datetime(production.startDate)
    if production.endDate is not None:
        update_data["endDate"] = format_datetime(production.endDate)
    if production.productionCompany is not None:
        update_data["productionCompany"] = production.productionCompany
    if production.episodeCount is not None:
        update_data["episodeCount"] = production.episodeCount
    if production.status is not None:
        update_data["status"] = production.status
    if production.contact is not None:
        update_data["contact"] = production.contact
    if production.metadata is not None:
        update_data["metadata"] = production.metadata
    
    updated = await prisma.production.update(
        where={"id": production_id},
        data=update_data
    )
    
    return updated


@router.delete("/{production_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete production")
async def delete_production(production_id: str):
    """Delete a production."""
    existing = await prisma.production.find_unique(
        where={"id": production_id}
    )
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production with ID {production_id} not found"
        )
    
    await prisma.production.delete(
        where={"id": production_id}
    )
    
    return None





