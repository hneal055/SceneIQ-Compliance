"""
scenes.py — AURA → SceneIQ scene import endpoint
POST /productions/{production_id}/scenes/import-from-aura
Accepts a structured scene list from AURA's /api/scenes/extract endpoint
and upserts into the scenes table, deduplicating by sceneNumber.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/productions",
    tags=["Scenes"],
)

from src.utils.database import prisma


class SceneImport(BaseModel):
    sceneNumber: str
    title: Optional[str] = None
    location: Optional[str] = None
    locationType: Optional[str] = None
    timeOfDay: Optional[str] = None
    pageCount: Optional[float] = None


class SceneImportRequest(BaseModel):
    scenes: List[SceneImport]


class SceneImportResponse(BaseModel):
    created: int
    skipped: int
    total: int
    warnings: List[str] = []


@router.post(
    "/{production_id}/scenes/import-from-aura",
    response_model=SceneImportResponse,
    summary="Import structured scene list from AURA scene extraction",
)
async def import_scenes_from_aura(
    production_id: str,
    body: SceneImportRequest,
):
    """Accept a scene list from AURA /api/scenes/extract and persist to the
    scenes table. Deduplicates by sceneNumber — existing scenes are skipped.
    """
    # Verify production exists
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Production {production_id!r} not found",
        )

    # Load existing scene numbers to avoid duplicates
    existing_rows = await prisma.scene.find_many(
        where={"productionId": production_id},
    )
    existing_numbers = {r.sceneNumber for r in existing_rows}

    created = 0
    skipped = 0
    warnings: List[str] = []

    for scene in body.scenes:
        if scene.sceneNumber in existing_numbers:
            skipped += 1
            warnings.append(
                f"Scene {scene.sceneNumber!r} already exists — skipped"
            )
            continue

        try:
            await prisma.scene.create(
                data={
                    "productionId": production_id,
                    "sceneNumber":  scene.sceneNumber,
                    "title":        scene.title,
                    "location":     scene.location,
                    "locationType": scene.locationType,
                    "timeOfDay":    scene.timeOfDay,
                    "pageCount":    scene.pageCount,
                }
            )
            existing_numbers.add(scene.sceneNumber)
            created += 1
        except Exception as exc:
            logger.exception(
                "scenes import: failed to create scene %s", scene.sceneNumber
            )
            warnings.append(
                f"Scene {scene.sceneNumber!r} failed to save: {exc}"
            )

    return SceneImportResponse(
        created=created,
        skipped=skipped,
        total=len(body.scenes),
        warnings=warnings,
    )
