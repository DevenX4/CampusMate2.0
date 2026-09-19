"""Users, roles and permissions. Tables only: login and authorization arrive in Phase 5."""

import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Index, Table, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Role(Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(primary_key=True)  # admin | faculty | student | guest
    name: Mapped[str]
    description: Mapped[str | None]


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(primary_key=True)  # e.g. documents:write
    description: Mapped[str | None]


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_code", ForeignKey("roles.code", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_code", ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True
    ),
)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Case-insensitive uniqueness: "A@x.com" and "a@x.com" are the same account.
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str]
    full_name: Mapped[str | None]
    password_hash: Mapped[str]  # never the password itself (hashing: Phase 5)
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    last_login_at: Mapped[datetime | None]
