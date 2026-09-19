"""FastAPI application entry point. Run with: uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.middleware import BodySizeLimit, add_request_id_middleware, add_security_headers_middleware
from app.api.routes import (
    audit, auth, chat, content, courses, departments, documents, faculty, ingestion, knowledge, programs, routing, search, system,
    users,
)
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.ingestion.background import BackgroundWorker

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("campusmate")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log where we would connect, never the password.
    logger.info(
        "Starting %s (env=%s, db=%s@%s:%s/%s)",
        settings.app_name, settings.app_env,
        settings.db_user, settings.db_host, settings.db_port, settings.db_name,
    )
    worker = BackgroundWorker() if settings.ingestion_in_api and settings.app_env != "test" else None
    if worker:
        worker.start()
    yield
    if worker:
        worker.stop()
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=version("campusmate-backend"),
    description=(
        "Every item carries its provenance. `source_type` is `official` (stated in a Ganpat "
        "University PDF), `derived_official` (computed from one) or `synthetic` (demo data, "
        "never a Ganpat University fact)."
    ),
    lifespan=lifespan,
    # The interactive API documentation is for development; production does not advertise its API.
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    openapi_url=None if settings.app_env == "production" else "/openapi.json",
)
register_error_handlers(app)
# Each middleware added wraps the ones before it. The body limit goes first, so it sits innermost:
# an error it raises while the route reads the body reaches FastAPI directly (the other layers
# run the app in a task group, which would re-wrap it as a generic 400).
app.add_middleware(BodySizeLimit, max_bytes=settings.max_body_kb * 1024)
add_request_id_middleware(app)
add_security_headers_middleware(app)
for module in (system, auth, users, audit, documents, ingestion, search, routing, chat,
               departments, programs, courses, faculty, knowledge, content):
    app.include_router(module.router, prefix=API_PREFIX)
