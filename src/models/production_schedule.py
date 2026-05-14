"""
Pydantic models for the Production Schedule Engine API
(src/api/production_schedule.py).

Kept deliberately minimal — only the shapes where `response_model=`
helps Swagger documentation. Dynamic dict responses (stripboard grid,
DOOD grid, jurisdiction summary list) come back as plain `dict` /
`list` so we don't have to mirror every Prisma model in Pydantic.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ImportResponse(BaseModel):
    """Result of POST /{production_id}/import."""
    scenes_imported: int = Field(..., description="How many Scene rows were persisted")
    jurisdictions_detected: List[str] = Field(
        default_factory=list,
        description="Unique jurisdiction NAMES seen in the uploaded file",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Per-row issues (unresolved jurisdiction names, etc.)",
    )


class AssignSceneBody(BaseModel):
    """Body for POST /{production_id}/stripboard/assign."""
    scene_id: str = Field(..., description="Scene.id to assign")
    shoot_day_id: str = Field(..., description="ShootDay.id to assign the scene to")
    # `position` is accepted for forward compat but currently a no-op —
    # the Scene model has no `position` column yet (see schema MVP note).
    position: Optional[int] = Field(
        None,
        description="Reserved for future explicit ordering — currently ignored",
    )


class JurisdictionSummaryRow(BaseModel):
    """One row in GET /{production_id}/jurisdiction-tracker."""
    jurisdiction_id: str
    jurisdiction_name: str
    shoot_days: int
    verified_at: Optional[datetime] = None
