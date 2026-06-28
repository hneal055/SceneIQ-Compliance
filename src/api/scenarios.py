"""
User Scenarios API â€” per-user Maximizer scenario persistence.

Replaces localStorage with DB-backed storage so scenarios survive across
devices and sessions. Tied to the authenticated user via JWT.

Endpoints:
  GET    /scenarios         â†’ list all scenarios for current user
  POST   /scenarios         â†’ create a new scenario
  DELETE /scenarios/{id}    â†’ delete a scenario (must belong to current user)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.utils.database import prisma
from src.utils.auth_utils import get_current_user
from src.models.user import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


# â”€â”€ Pydantic models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ScenarioCreate(BaseModel):
    name:        str         = Field(..., min_length=1, max_length=120)
    codes:       str         = Field(..., description="Space/comma-separated jurisdiction codes")
    spend:       str         = Field(..., description="Qualified spend as entered (raw string)")
    projectType: str         = Field(default="film")
    splitSpend:  dict        = Field(default_factory=dict)


class ScenarioOut(BaseModel):
    id:          str
    name:        str
    codes:       str
    spend:       str
    projectType: str
    splitSpend:  dict
    savedAt:     str          # ISO string â€” matches SavedScenario.savedAt in frontend

    model_config = {"from_attributes": True}


def _to_out(row) -> ScenarioOut:
    return ScenarioOut(
        id=row.id,
        name=row.name,
        codes=row.codes,
        spend=row.spend,
        projectType=row.projectType,
        splitSpend=row.splitSpend if isinstance(row.splitSpend, dict) else {},
        savedAt=row.createdAt.isoformat() if row.createdAt else "",
    )


# â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("", summary="List current user's saved scenarios")
async def list_scenarios(current_user: TokenData = Depends(get_current_user)):
    rows = await prisma.userScenario.find_many(
        where={"userId": current_user.sub},
        order={"createdAt": "desc"},
    )
    return [_to_out(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Save a Maximizer scenario")
async def create_scenario(
    data: ScenarioCreate,
    current_user: TokenData = Depends(get_current_user),
):
    row = await prisma.userScenario.create(data={
        "userId":      current_user.sub,
        "name":        data.name,
        "codes":       data.codes,
        "spend":       data.spend,
        "projectType": data.projectType,
        "splitSpend":  data.splitSpend,
    })
    logger.info(f"Scenario '{data.name}' created for user {current_user.email}")
    return _to_out(row)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a saved scenario")
async def delete_scenario(
    scenario_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    row = await prisma.userScenario.find_unique(where={"id": scenario_id})
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scenario not found")
    if row.userId != current_user.sub:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your scenario")
    await prisma.userScenario.delete(where={"id": scenario_id})
    return None



