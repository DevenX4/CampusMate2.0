"""Reusable endpoint parameters and the authentication/authorization dependencies.

`Annotated[...]` bundles a type with how FastAPI obtains and validates it, so every endpoint
declares e.g. `limit: Limit` or `user: CurrentUser` the same way.
"""

import ipaddress
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.auth import User
from app.schemas.common import ErrorResponse
from app.services import auth
from app.services.audit import RequestContext

DbSession = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100, description="Maximum number of items to return")]
Offset = Annotated[int, Query(ge=0, description="Number of items to skip (for paging)")]
SearchText = Annotated[str | None, Query(min_length=1, max_length=100)]

NOT_FOUND = {404: {"model": ErrorResponse, "description": "No such resource"}}
AUTH_ERRORS = {
    401: {"model": ErrorResponse, "description": "Not logged in, or the session expired"},
    403: {"model": ErrorResponse, "description": "Logged in, but the role lacks the permission"},
}

SESSION_COOKIE = "campusmate_session"
# auto_error=False: a missing header is not an error here; the endpoint's permission decides.
_bearer = HTTPBearer(auto_error=False, description="Session token from POST /api/v1/auth/login")


def session_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    """The token from `Authorization: Bearer ...` (API clients) or the session cookie (browser)."""
    if credentials is not None:
        return credentials.credentials
    return request.cookies.get(SESSION_COOKIE)


def current_user_or_none(db: DbSession, token: Annotated[str | None, Depends(session_token)]) -> User | None:
    return auth.user_for_token(db, token) if token else None


def current_user(user: Annotated[User | None, Depends(current_user_or_none)]) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require(permission: str):
    """Dependency factory: allow the request only if the caller's role has `permission`.
    Visitors who are not logged in get the permissions of the 'guest' role. The role is always
    read from the database, never from anything the client sends."""

    def check(db: DbSession, user: Annotated[User | None, Depends(current_user_or_none)]) -> User | None:
        role = user.role_code if user else auth.GUEST_ROLE
        if permission in auth.permissions_of(db, role):
            return user
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                                headers={"WWW-Authenticate": "Bearer"})
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            f"Role '{role}' does not have the '{permission}' permission")

    return check


def request_context(request: Request) -> RequestContext:
    host = request.client.host if request.client else None
    try:
        ip = str(ipaddress.ip_address(host)) if host else None
    except ValueError:  # e.g. "testclient"
        ip = None
    return RequestContext(ip_address=ip, user_agent=request.headers.get("user-agent"),
                          request_id=getattr(request.state, "request_id", None))


Context = Annotated[RequestContext, Depends(request_context)]
