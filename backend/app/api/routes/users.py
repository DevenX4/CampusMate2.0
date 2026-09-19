import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status

from app.api.deps import AUTH_ERRORS, NOT_FOUND, Context, DbSession, Limit, Offset, SearchText, require
from app.models.auth import User
from app.schemas.common import ErrorResponse, Page
from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.services import users

router = APIRouter(prefix="/users", tags=["users"], responses=AUTH_ERRORS)
Admin = Annotated[User, Depends(require("users:manage"))]
CONFLICT = {409: {"model": ErrorResponse, "description": "Email in use, or change not allowed"}}


@router.get("", response_model=Page[UserOut])
def list_users(db: DbSession, admin: Admin, q: SearchText = None,
               role: Literal["admin", "faculty", "student"] | None = None,
               limit: Limit = 20, offset: Offset = 0):
    return users.list_users(db, q=q, role=role, limit=limit, offset=offset)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, responses=CONFLICT)
def create_user(body: UserCreate, db: DbSession, admin: Admin, context: Context):
    return users.create_user(db, body, actor_id=admin.id, context=context)


@router.patch("/{user_id}", response_model=UserOut, responses={**NOT_FOUND, **CONFLICT})
def update_user(user_id: uuid.UUID, body: UserUpdate, db: DbSession, admin: Admin, context: Context):
    """Change name, role, active flag or password. Deactivating an account or changing its
    password ends all of that user's sessions immediately."""
    return users.update_user(db, user_id, body, actor=admin, context=context)
