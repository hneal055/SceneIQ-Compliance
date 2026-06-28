"""Pydantic models for authentication."""

from __future__ import annotations

from pydantic import BaseModel


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    isActive: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: str
    email: str
    role: str




