"""
Notification Preferences API â€” per-user email alert subscriptions and report schedule.
"""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma
from src.utils.auth_utils import get_current_user
from src.models.user import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


# â”€â”€ Pydantic models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PrefUpsert(BaseModel):
    emailAddress:    str
    jurisdictions:   list[str]                        = []       # empty = all
    active:          bool                             = True
    reportFrequency: Literal["daily", "weekly", "never"] = "never"


# â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/preferences", summary="Get current user's notification preferences")
async def get_preferences(current_user: TokenData = Depends(get_current_user)):
    pref = await prisma.notificationpreference.find_unique(
        where={"userId": current_user.sub}
    )
    return pref  # None if not set yet


@router.post("/preferences", summary="Create or update notification preferences")
async def upsert_preferences(
    data: PrefUpsert,
    current_user: TokenData = Depends(get_current_user),
):
    existing = await prisma.notificationpreference.find_unique(
        where={"userId": current_user.sub}
    )
    if existing:
        pref = await prisma.notificationpreference.update(
            where={"userId": current_user.sub},
            data={
                "emailAddress":    data.emailAddress,
                "jurisdictions":   data.jurisdictions,
                "active":          data.active,
                "reportFrequency": data.reportFrequency,
            },
        )
    else:
        user = await prisma.user.find_unique(where={"id": current_user.sub})
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        pref = await prisma.notificationpreference.create(data={
            "userId":          current_user.sub,
            "emailAddress":    data.emailAddress,
            "jurisdictions":   data.jurisdictions,
            "active":          data.active,
            "reportFrequency": data.reportFrequency,
        })
    logger.info(f"Notification preferences updated for user {current_user.email}")
    return pref


@router.delete("/preferences",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Remove notification preferences")
async def delete_preferences(current_user: TokenData = Depends(get_current_user)):
    existing = await prisma.notificationpreference.find_unique(
        where={"userId": current_user.sub}
    )
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No preferences found")
    await prisma.notificationpreference.delete(where={"userId": current_user.sub})
    return None





