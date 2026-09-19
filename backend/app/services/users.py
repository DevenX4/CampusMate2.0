"""User accounts: create, list, update. There is deliberately no delete: accounts with audit
history are deactivated instead, so the history keeps pointing at a real account."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.auth import Role, User
from app.schemas.common import Page
from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.services import audit
from app.services.audit import RequestContext
from app.services.auth import GUEST_ROLE, find_user_by_email, revoke_all_sessions
from app.services.errors import ConflictError, NotFoundError
from app.services.helpers import contains, paginate


def _check_role(db: Session, role_code: str) -> None:
    if role_code == GUEST_ROLE:
        raise ConflictError("'guest' is the role of visitors who are not logged in; it cannot be assigned")
    if db.get(Role, role_code) is None:
        raise NotFoundError("Role", role_code)


def list_users(db: Session, *, q: str | None, role: str | None, limit: int, offset: int) -> Page[UserOut]:
    query = select(User).order_by(User.email)
    if q:
        query = query.where(contains(User.email, q) | contains(User.full_name, q))
    if role:
        query = query.where(User.role_code == role)
    return paginate(db, query, UserOut, limit, offset)


def create_user(db: Session, data: UserCreate, *, actor_id: uuid.UUID | None, context: RequestContext) -> UserOut:
    _check_role(db, data.role)
    if find_user_by_email(db, data.email):
        raise ConflictError(f"A user with email {data.email} already exists")
    user = User(email=data.email.lower(), full_name=data.full_name,
                password_hash=hash_password(data.password), role_code=data.role)
    db.add(user)
    db.flush()  # assigns user.id
    audit.record(db, "user.create", actor_id=actor_id, context=context, entity_type="user",
                 entity_id=str(user.id), details={"email": user.email, "role": user.role_code})
    db.commit()
    return UserOut.model_validate(user)


def update_user(db: Session, user_id: uuid.UUID, data: UserUpdate, *, actor: User, context: RequestContext) -> UserOut:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User", str(user_id))
    # Guard against locking the last door: an admin cannot demote or deactivate themselves.
    if user.id == actor.id and (data.role not in (None, user.role_code) or data.is_active is False):
        raise ConflictError("You cannot change your own role or deactivate your own account")

    # Fields actually sent; an explicit null only means something for full_name.
    changes = {k: v for k, v in data.model_dump(exclude_unset=True, exclude={"password"}).items()
               if v is not None or k == "full_name"}
    if data.role is not None:
        _check_role(db, data.role)
    for field, value in changes.items():
        setattr(user, "role_code" if field == "role" else field, value)
    if data.password is not None:
        user.password_hash = hash_password(data.password)
        changes["password"] = "changed"  # the audit log records THAT it changed, never the value
    if data.is_active is False or data.password is not None:
        revoke_all_sessions(db, user)  # takes effect immediately, on every device

    audit.record(db, "user.update", actor_id=actor.id, context=context, entity_type="user",
                 entity_id=str(user.id), details=changes)
    db.commit()
    return UserOut.model_validate(user)
