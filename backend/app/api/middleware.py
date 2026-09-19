"""Request ID: one identifier per HTTP request, echoed in the X-Request-ID response header and
stored in audit entries, so a user's error report can be matched to exactly one log line."""

import re
import uuid

from fastapi import FastAPI, Request

# Accept a caller-supplied ID only if it is short and harmless (it ends up in logs).
_SAFE_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")


def add_request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request.state.request_id = incoming if _SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response
