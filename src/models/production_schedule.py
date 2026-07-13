"""
Pydantic models for the Production Schedule Engine API
(src/api/production_schedule.py).

Kept deliberately minimal â€” only the shapes where `response_model=`
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
    # `position` is accepted for forward compat but currently a no-op â€”
    # the Scene model has no `position` column yet (see schema MVP note).
    position: Optional[int] = Field(
        None,
        description="Reserved for future explicit ordering â€” currently ignored",
    )


class UnassignSceneBody(BaseModel):
    """Body for POST /{production_id}/stripboard/unassign â€” moves a scene
    back to the Unscheduled bin by clearing its shootDayId."""
    scene_id: str = Field(..., description="Scene.id to move back to Unscheduled")


class CrewCallItem(BaseModel):
    """One row in a shoot day's Crew Calls table."""
    department: Optional[str] = None
    name: Optional[str] = None
    call_time: Optional[str] = Field(None, description="e.g. '05:30 AM'")
    wrap_time: Optional[str] = Field(None, description="e.g. '11:30 PM'")


class CreateShootDayBody(BaseModel):
    """Body for POST /{production_id}/shoot-days. Every field is optional;
    the day_number is assigned automatically (max existing + 1). A blank day
    is created when no fields are supplied â€” the user fills it in by assigning
    scenes from the Unscheduled bin."""
    date: Optional[str] = Field(None, description="ISO date string (YYYY-MM-DD)")
    jurisdiction_name: Optional[str] = Field(
        None, description="Jurisdiction NAME; resolved to a FK id server-side"
    )
    location: Optional[str] = None
    call_time: Optional[str] = Field(None, description="e.g. '06:00 AM'")
    wrap_time: Optional[str] = Field(None, description="e.g. '11:30 PM'")
    nearest_hospital: Optional[str] = None
    notes: Optional[str] = None


class UpdateShootDayBody(BaseModel):
    """Body for PATCH /{production_id}/shoot-days/{shoot_day_id}. The edit
    form always sends every field, so each is overwritten with the supplied
    value (an empty value clears the field). day_number and scene assignments
    are managed separately and are not editable here."""
    date: Optional[str] = Field(None, description="ISO date string (YYYY-MM-DD)")
    jurisdiction_name: Optional[str] = Field(
        None, description="Jurisdiction NAME; resolved to a FK id server-side. Empty clears it."
    )
    location: Optional[str] = None
    call_time: Optional[str] = Field(None, description="e.g. '06:00 AM'")
    wrap_time: Optional[str] = Field(None, description="e.g. '11:30 PM'")
    nearest_hospital: Optional[str] = None
    notes: Optional[str] = None
    crew_calls: Optional[List[CrewCallItem]] = Field(
        None, description="Full replacement list of department call times"
    )


class JurisdictionSummaryRow(BaseModel):
    """One row in GET /{production_id}/jurisdiction-tracker."""
    jurisdiction_id: str
    jurisdiction_name: str
    shoot_days: int
    verified_at: Optional[datetime] = None




