"""
Admin API — user management (list, create, update role/status, delete).
All endpoints require admin role.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.utils.database import prisma
from src.utils.auth_utils import get_current_user, hash_password
from src.models.user import TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Auth dependency ───────────────────────────────────────────────────────────

def _require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return current_user


# ── Pydantic models ───────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email:    str
    password: str
    role:     str = "viewer"


class UserUpdate(BaseModel):
    role:     Optional[str] = None
    isActive: Optional[bool] = None
    password: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/users", summary="List all users")
async def list_users(_: TokenData = Depends(_require_admin)):
    users = await prisma.user.find_many(order={"createdAt": "asc"})
    return {
        "total": len(users),
        "users": [
            {
                "id":        u.id,
                "email":     u.email,
                "role":      u.role,
                "isActive":  u.isActive,
                "createdAt": u.createdAt,
                "updatedAt": u.updatedAt,
            }
            for u in users
        ],
    }


@router.post("/users",
             status_code=status.HTTP_201_CREATED,
             summary="Create a new user")
async def create_user(data: UserCreate, _: TokenData = Depends(_require_admin)):
    existing = await prisma.user.find_unique(where={"email": data.email})
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email already in use: {data.email}")

    if data.role not in ("admin", "viewer"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Role must be 'admin' or 'viewer'")

    user = await prisma.user.create(data={
        "email":        data.email,
        "passwordHash": hash_password(data.password),
        "role":         data.role,
        "isActive":     True,
    })
    logger.info(f"Admin created user: {user.email} (role={user.role})")
    return {"id": user.id, "email": user.email, "role": user.role, "isActive": user.isActive}


@router.patch("/users/{user_id}", summary="Update user role, status, or password")
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_admin: TokenData = Depends(_require_admin),
):
    user = await prisma.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    update: dict = {}
    if data.role is not None:
        if data.role not in ("admin", "viewer"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Role must be 'admin' or 'viewer'")
        update["role"] = data.role
    if data.isActive is not None:
        # Prevent self-deactivation
        if user_id == current_admin.sub and not data.isActive:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate your own account")
        update["isActive"] = data.isActive
    if data.password is not None:
        update["passwordHash"] = hash_password(data.password)

    if not update:
        return user

    updated = await prisma.user.update(where={"id": user_id}, data=update)
    logger.info(f"Admin updated user {updated.email}: {list(update.keys())}")
    return {"id": updated.id, "email": updated.email, "role": updated.role, "isActive": updated.isActive}


@router.delete("/users/{user_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a user")
async def delete_user(
    user_id: str,
    current_admin: TokenData = Depends(_require_admin),
):
    if user_id == current_admin.sub:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete your own account")

    user = await prisma.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    await prisma.user.delete(where={"id": user_id})
    logger.info(f"Admin deleted user: {user.email}")
    return None
