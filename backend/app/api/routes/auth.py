from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import AUTH_ERRORS, SESSION_COOKIE, Context, CurrentUser, DbSession, session_token
from app.core.config import get_settings
from app.schemas.common import ErrorResponse
from app.schemas.users import LoginRequest, LoginResponse, Me, UserOut
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse,
             responses={401: {"model": ErrorResponse, "description": "Invalid email or password"}})
def login(body: LoginRequest, response: Response, db: DbSession, context: Context):
    """Open a session. The token is set as an httpOnly cookie (for browsers) and also
    returned in the body (for API clients such as curl or the /docs Authorize button)."""
    settings = get_settings()
    result = auth.login(db, body.email, body.password, ttl_hours=settings.session_ttl_hours, context=context)
    if result is None:
        # Deliberately vague: never reveal whether the email exists.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
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


@router.get("/me", response_model=Me, responses=AUTH_ERRORS)
def me(user: CurrentUser, db: DbSession):
    return Me(user=UserOut.model_validate(user), permissions=sorted(auth.permissions_of(db, user.role_code)))
