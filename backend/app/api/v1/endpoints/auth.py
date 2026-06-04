from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.security import (
    verify_password,
    hash_password,
    validate_password_complexity,
    create_access_token,
    is_account_locked,
    lockout_expiry,
    MAX_FAILED_ATTEMPTS,
)
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": request.email}).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    user = row._mapping
    if is_account_locked(user["lockedUntil"]):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked. Try again in 15 minutes.")
    if not verify_password(request.password, user["passwordHash"]):
        new_count = (user["failedLoginCount"] or 0) + 1
        if new_count >= MAX_FAILED_ATTEMPTS:
            db.execute(text('UPDATE users SET "failedLoginCount" = :count, "lockedUntil" = :locked WHERE email = :email'),
                {"count": new_count, "locked": lockout_expiry(), "email": request.email})
            db.commit()
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account locked. Try again in 15 minutes.")
        db.execute(text('UPDATE users SET "failedLoginCount" = :count WHERE email = :email'),
            {"count": new_count, "email": request.email})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    db.execute(text('UPDATE users SET "failedLoginCount" = 0, "lockedUntil" = NULL, "lastLoginAt" = :now WHERE email = :email'),
        {"now": datetime.now(timezone.utc), "email": request.email})
    db.commit()
    token = create_access_token(data={"sub": user["email"], "role": user["role"]})
    return TokenResponse(access_token=token)

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    valid, reason = validate_password_complexity(request.password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=reason)
    existing = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": request.email}).fetchone()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")
    db.execute(text("""
        INSERT INTO users (id, email, "passwordHash", "fullName", role, "isActive", "failedLoginCount", "createdAt", "updatedAt")
        VALUES (gen_random_uuid()::text, :email, :password, :full_name, 'viewer', true, 0, now(), now())
    """), {"email": request.email, "password": hash_password(request.password), "full_name": request.full_name})
    db.commit()
    return {"message": "Account created successfully.", "email": request.email}
