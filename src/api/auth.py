"""Authentication endpoints: login + me."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.utils.database import prisma
from src.utils.config import settings
from src.models.user import Token, UserLogin, UserResponse, TokenData
from src.utils.auth_utils import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
_LOCKED = HTTPException(
    status_code=status.HTTP_423_LOCKED,
    detail=f"Account locked. Try again in {settings.LOCKOUT_MINUTES} minutes.",
)


def _is_locked(locked_until) -> bool:
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < locked_until


async def _authenticate(email: str, password: str) -> Token:
    """Shared authentication logic for both login endpoints.

    Enforces account lockout after settings.MAX_FAILED_ATTEMPTS consecutive
    failures (423), and resets the counter on a successful login.
    """
    user = await prisma.user.find_unique(where={"email": email})
    if not user or not user.isActive:
        raise _INVALID_CREDENTIALS

    if _is_locked(user.lockedUntil):
        raise _LOCKED

    if not verify_password(password, user.passwordHash):
        new_count = (user.failedLoginCount or 0) + 1
        if new_count >= settings.MAX_FAILED_ATTEMPTS:
            await prisma.user.update(
                where={"id": user.id},
                data={
                    "failedLoginCount": new_count,
                    "lockedUntil": datetime.now(timezone.utc)
                    + timedelta(minutes=settings.LOCKOUT_MINUTES),
                },
            )
            raise _LOCKED
        await prisma.user.update(
            where={"id": user.id}, data={"failedLoginCount": new_count}
        )
        raise _INVALID_CREDENTIALS

    # Success â€” clear any failure state and stamp last login.
    await prisma.user.update(
        where={"id": user.id},
        data={
            "failedLoginCount": 0,
            "lockedUntil": None,
            "lastLoginAt": datetime.now(timezone.utc),
        },
    )
    token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
        }
    )
    return Token(access_token=token)


@router.post("/token", response_model=Token, include_in_schema=False)
async def token(request: Request):
    """OAuth2 password flow â€” used by Swagger UI Authorize button.
    Accepts application/x-www-form-urlencoded (username + password fields).
    """
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    return await _authenticate(username, password)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    return await _authenticate(credentials.email, credentials.password)


@router.get("/me", response_model=UserResponse)
async def me(current_user: TokenData = Depends(get_current_user)):
    user = await prisma.user.find_unique(where={"id": current_user.sub})
    if not user or not user.isActive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        isActive=user.isActive,
    )



