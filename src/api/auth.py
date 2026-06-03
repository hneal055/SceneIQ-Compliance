"""Authentication endpoints: login + me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.utils.database import prisma
from src.models.user import Token, UserLogin, UserResponse, TokenData
from src.utils.auth_utils import create_access_token, get_current_user, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


async def _authenticate(email: str, password: str) -> Token:
    """Shared authentication logic for both login endpoints."""
    user = await prisma.user.find_unique(where={"email": email})
    if not user or not user.isActive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
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
    """OAuth2 password flow — used by Swagger UI Authorize button.
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
