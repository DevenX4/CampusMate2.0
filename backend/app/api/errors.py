"""One error format for every failure:

    {"error": {"code": "not_found", "message": "Course 'COURSE-X' not found", "details": null}}

Clients (the React app, tests, the chat pipeline) can always read error.code, whatever went wrong.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware import BodyTooLarge
from app.services.errors import ConflictError, NotFoundError, RateLimited, UploadRejected

logger = logging.getLogger(__name__)


def error_response(status_code: int, code: str, message: str, details: list | None = None,
                   headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
        headers=headers,
    )


async def not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return error_response(status.HTTP_404_NOT_FOUND, "not_found", str(exc))


async def conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return error_response(status.HTTP_409_CONFLICT, "conflict", str(exc))


UPLOAD_STATUS = {
    "too_large": status.HTTP_413_CONTENT_TOO_LARGE,
    "unsupported_type": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "invalid": status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def upload_rejected(request: Request, exc: UploadRejected) -> JSONResponse:
    return error_response(UPLOAD_STATUS[exc.kind], f"upload_{exc.kind}", str(exc))


async def rate_limited(request: Request, exc: RateLimited) -> JSONResponse:
    return error_response(status.HTTP_429_TOO_MANY_REQUESTS, "rate_limited", str(exc),
                          headers={"Retry-After": str(exc.retry_after)})


async def body_too_large(request: Request, exc: BodyTooLarge) -> JSONResponse:
    return error_response(status.HTTP_413_CONTENT_TOO_LARGE, "body_too_large", exc.detail)


async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    # e.g. ?limit=0 -> [{"location": "query.limit", "message": "Input should be greater than or equal to 1"}]
    details = [
        {"location": ".".join(str(part) for part in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", "The request is invalid.", details
    )


async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Framework-level errors such as an unknown URL (404) or a wrong method (405).
    code = HTTPStatus(exc.status_code).phrase.lower().replace(" ", "_")
    # Keep headers such as WWW-Authenticate on 401 responses.
    return error_response(exc.status_code, code, str(exc.detail), headers=exc.headers)


async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Full details go to the log only; the client never sees stack traces or SQL.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred."
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, not_found)
    app.add_exception_handler(ConflictError, conflict)
    app.add_exception_handler(UploadRejected, upload_rejected)
    app.add_exception_handler(RateLimited, rate_limited)
    app.add_exception_handler(BodyTooLarge, body_too_large)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(StarletteHTTPException, http_error)
    app.add_exception_handler(Exception, unexpected_error)
