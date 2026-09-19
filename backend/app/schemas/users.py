"""Request and response shapes for login and user management.
A password hash is never part of any response schema."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import FromORM

AssignableRole = Literal["admin", "faculty", "student"]
PASSWORD_RULES = {"min_length": 10, "max_length": 128, "description": "At least 10 characters"}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(FromORM):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str = Field(validation_alias="role_code")
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class LoginResponse(BaseModel):
    access_token: str = Field(description="Also set as an httpOnly cookie; browsers should rely on the cookie")
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserOut


class Me(BaseModel):
    user: UserOut
    permissions: list[str]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=200)
    password: str = Field(**PASSWORD_RULES)
    role: AssignableRole


class UserUpdate(BaseModel):
    """Only the fields sent are changed (PATCH semantics)."""

    full_name: str | None = Field(default=None, max_length=200)
    role: AssignableRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, **PASSWORD_RULES)
