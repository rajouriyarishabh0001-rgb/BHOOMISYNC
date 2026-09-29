import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from database.session import get_db
from models.core import PasswordResetToken, Role, User
from schemas.auth import CreatePasswordRequest, ForgotPasswordRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from security import create_access_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])
RESET_GENERIC_MESSAGE = "If an account exists for that email, password reset instructions have been generated."


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, name=user.name, email=user.email, phone=user.phone, department=user.department, role=user.role.name, is_active=user.is_active, is_verified=user.is_verified, created_at=user.created_at)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(request: RegisterRequest, session: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    if session.scalar(select(User).where(User.email == request.email.lower())):
        raise HTTPException(409, "An account with this email already exists")
    role = session.scalar(select(Role).where(Role.name == request.role.upper()))
    if not role:
        raise HTTPException(400, "Unsupported role")
    user = User(name=request.name, email=request.email.lower(), phone=request.phone, password_hash=hash_password(request.password), role=role, department=request.department, is_verified=False)
    session.add(user); session.commit(); session.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=user_response(user))


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, session: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = session.scalar(select(User).options(joinedload(User.role)).where(User.email == request.email.lower()))
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    user.last_login = datetime.now(timezone.utc); session.commit()
    return TokenResponse(access_token=create_access_token(user), user=user_response(user))


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, session: Annotated[Session, Depends(get_db)]) -> dict[str, str | None]:
    user = session.scalar(select(User).where(User.email == request.email.lower()))
    response: dict[str, str | None] = {"message": RESET_GENERIC_MESSAGE, "reset_token": None}
    if not user or not user.is_active:
        return response
    raw_token = secrets.token_urlsafe(32)
    session.add(PasswordResetToken(user_id=user.id, token_hash=token_digest(raw_token), expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)))
    session.commit()
    if os.getenv("RESET_TOKEN_EXPOSED", "false").lower() == "true":
        response["reset_token"] = raw_token
    return response


@router.post("/create-password")
def create_password(request: CreatePasswordRequest, session: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    reset = session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_digest(request.token), PasswordResetToken.used_at.is_(None)))
    if not reset or reset.expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This password reset link is invalid or expired.")
    user = session.scalar(select(User).where(User.id == reset.user_id))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This password reset link is invalid or expired.")
    user.password_hash = hash_password(request.password)
    reset.used_at = now
    session.commit()
    return {"message": "Password created successfully. You can now sign in."}


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(current_user)]) -> UserResponse:
    return user_response(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(user: Annotated[User, Depends(current_user)]) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user), user=user_response(user))


@router.post("/logout", status_code=204)
def logout(_: Annotated[User, Depends(current_user)]) -> None:
    return None