from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    role: str = "CITIZEN"
    department: str | None = None


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)


class CreatePasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    email: str
    phone: str | None
    department: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse