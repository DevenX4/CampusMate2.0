from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import AUTH_ERRORS, SESSION_COOKIE, Context, CurrentUser, DbSession, session_token
from app.core.config import get_settings
from app.schemas.common import ErrorResponse
from app.models.auth import User
from app.schemas.users import DemoAccount, DemoAccounts, LoginRequest, LoginResponse, Me, UserOut
from app.services import auth, users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse,
             responses={401: {"model": ErrorResponse, "description": "Invalid username or password"},
                        429: {"model": ErrorResponse, "description": "Too many failed attempts; see Retry-After"}})
def login(body: LoginRequest, response: Response, db: DbSession, context: Context):
    """Open a session. The token is set as an httpOnly cookie (for browsers) and also
    returned in the body (for API clients such as curl or the /docs Authorize button)."""
    settings = get_settings()
    limits = auth.LoginLimits(settings.login_max_failures, settings.login_max_failures_per_ip,
                              settings.login_window_minutes)
    result = auth.login(db, body.username, body.password, ttl_hours=settings.session_ttl_hours, context=context,
                        limits=limits, allow_demo=settings.app_env != "production")
    if result is None:
        # Deliberately vague: never reveal whether the email exists.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password.")
    response.set_cookie(
        SESSION_COOKIE, result.token, max_age=settings.session_ttl_hours * 3600,
        httponly=True,           # JavaScript cannot read it, so XSS cannot steal it
        samesite="lax",          # not sent on cross-site POSTs (CSRF protection)
        secure=settings.cookie_secure, path="/",
    )
    return LoginResponse(access_token=result.token, expires_at=result.expires_at,
                         user=UserOut.model_validate(result.user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: DbSession, context: Context,
           token: Annotated[str | None, Depends(session_token)]):
    """End the current session (idempotent: logging out twice is fine)."""
    if token:
        auth.logout(db, token, context=context)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/demo", response_model=DemoAccounts)
def demo_accounts(db: DbSession):
    """The local demo accounts and their (public) passwords, for the login page. Empty in
    production, where demo accounts cannot log in."""
    if get_settings().app_env == "production":
        return DemoAccounts(enabled=False, accounts=[])
    present = set(db.scalars(select(User.username).where(User.is_demo, User.is_active)))
    accounts = [DemoAccount(username=u, password=p, role=r) for u, p, r, _, _ in users.DEMO_ACCOUNTS if u in present]
    return DemoAccounts(enabled=bool(accounts), accounts=accounts)


@router.get("/me", response_model=Me, responses=AUTH_ERRORS)
def me(user: CurrentUser, db: DbSession):
    return Me(user=UserOut.model_validate(user), permissions=sorted(auth.permissions_of(db, user.role_code)))
