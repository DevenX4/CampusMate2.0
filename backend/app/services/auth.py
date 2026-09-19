"""Login, sessions and permissions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import hash_password, needs_rehash, new_session_token, token_digest, verify_password
from app.models.auth import User, UserSession, role_permissions
from app.services import audit
from app.services.audit import RequestContext

GUEST_ROLE = "guest"


@dataclass
class LoginResult:
    user: User
    token: str  # returned to the client once; never stored
    expires_at: datetime


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def login(db: Session, email: str, password: str, *, ttl_hours: int, context: RequestContext) -> LoginResult | None:
    """Check the credentials and open a session. Returns None for ANY failure (unknown email,
    wrong password, deactivated account) so the caller cannot tell which one it was."""
    user = find_user_by_email(db, email)
    valid = verify_password(user.password_hash if user else None, password)
    if not valid or not user.is_active:
        # Actor unknown (whoever typed the password); the targeted account is the entity.
        audit.record(db, "auth.login_failed", actor_id=None, context=context, entity_type="user",
                     entity_id=str(user.id) if user else None, details={"email": email.lower()})
        db.commit()
        return None

    if needs_rehash(user.password_hash):  # hashing parameters were strengthened since
        user.password_hash = hash_password(password)
    token = new_session_token()
    now = datetime.now(UTC)
    session = UserSession(
        user_id=user.id, token_sha256=token_digest(token), created_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
        ip_address=context.ip_address, user_agent=(context.user_agent or "")[:300] or None,
    )
    user.last_login_at = now
    db.add(session)
    audit.record(db, "auth.login", actor_id=user.id, context=context,
                 entity_type="user", entity_id=str(user.id))
    db.commit()
    return LoginResult(user=user, token=token, expires_at=session.expires_at)


def user_for_token(db: Session, token: str) -> User | None:
    """The active user owning a valid (not revoked, not expired) session, else None."""
    return db.scalar(
        select(User).join(UserSession, UserSession.user_id == User.id).where(
            UserSession.token_sha256 == token_digest(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > func.now(),
            User.is_active.is_(True),
        )
    )


def logout(db: Session, token: str, *, context: RequestContext) -> None:
    session = db.scalar(select(UserSession).where(UserSession.token_sha256 == token_digest(token)))
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        audit.record(db, "auth.logout", actor_id=session.user_id, context=context,
                     entity_type="user", entity_id=str(session.user_id))
        db.commit()


def revoke_all_sessions(db: Session, user: User) -> None:
    """Used when an account is deactivated: every open session stops working at once."""
    db.execute(update(UserSession)
               .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
               .values(revoked_at=func.now()))


def permissions_of(db: Session, role_code: str) -> set[str]:
    return set(db.scalars(
        select(role_permissions.c.permission_code).where(role_permissions.c.role_code == role_code)
    ))
