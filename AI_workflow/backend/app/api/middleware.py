"""HTTP middleware:

- request ID: one identifier per request, echoed in X-Request-ID and stored in audit entries, so a
  user's error report can be matched to exactly one log line;
- security headers on every response;
- a size limit on request bodies (uploads excepted: they are streamed with their own limit).
"""

import json
import re
import uuid

from fastapi import FastAPI, HTTPException, Request

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


# The API returns JSON only: nothing may frame it, run scripts in it, or cache it (answers and
# audit data are personal). The UI's own headers are set by whatever serves the built UI.
_API_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}
_COMMON_HEADERS = {
    "X-Content-Type-Options": "nosniff",  # no guessing a JSON or PDF response is HTML
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


def add_security_headers_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in _COMMON_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/api/"):
            for name, value in _API_HEADERS.items():
                response.headers.setdefault(name, value)
        return response


class BodyTooLarge(HTTPException):
    """FastAPI's HTTPException, because FastAPI turns any other error raised while reading a body
    (Starlette's HTTPException included) into a generic 400; this one passes through to its own
    413 handler."""

    def __init__(self, message: str):
        super().__init__(413, message)


class BodySizeLimit:
    """Rejects request bodies over `max_bytes` (413), by Content-Length and, for chunked requests
    that have none, while reading. Multipart uploads are exempt: the upload endpoints stream them
    to disk with MAX_UPLOAD_MB. Without this, one huge JSON body would be parsed into memory."""

    def __init__(self, app, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        if headers.get(b"content-type", b"").startswith(b"multipart/form-data"):
            return await self.app(scope, receive, send)
        declared = headers.get(b"content-length")
        too_large = f"The request body is larger than {self.max_bytes // 1024} KB."
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            return await _plain_413(send, too_large)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLarge(too_large)
            return message

        await self.app(scope, limited_receive, send)


async def _plain_413(send, message: str) -> None:
    body = json.dumps({"error": {"code": "body_too_large", "message": message, "details": None}}).encode()
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})
