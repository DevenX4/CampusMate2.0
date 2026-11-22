"""Users, roles, permissions and login sessions.

Roles and permissions are reference data inserted by a migration, because code depends on them."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Table, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import INET
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
        # Usernames are stored lower case, so a plain unique constraint is case-insensitive.
        UniqueConstraint("username"),
        CheckConstraint(r"username ~ '^[a-z0-9][a-z0-9._-]{2,39}$'", name="username_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str]
    username: Mapped[str | None]  # optional short login name, e.g. "admin"
    full_name: Mapped[str | None]
    password_hash: Mapped[str]  # Argon2 hash, never the password itself
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    last_login_at: Mapped[datetime | None]
    # A demo account (python -m app.accounts demo): a public, deliberately simple password, so it
    # can never log in when APP_ENV=production.
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))


class UserSession(Base):
    """One login. The token itself is only ever held by the client; we store its SHA-256.
    A session is valid while not revoked and not expired, so logout and deactivation take
    effect immediately (unlike a self-contained JWT)."""

    __tablename__ = "user_sessions"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="expiry_after_creation"),
        Index("ix_user_sessions_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_sha256: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None]
