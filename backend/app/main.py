"""FastAPI application entry point. Run with: uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import courses, departments, faculty, programs, system
from app.core.config import get_settings
from app.core.logging import setup_logging

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
    yield
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
)
register_error_handlers(app)
for module in (system, departments, programs, courses, faculty):
    app.include_router(module.router, prefix=API_PREFIX)
