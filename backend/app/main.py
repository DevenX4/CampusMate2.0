"""FastAPI application entry point. Run with: uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from app.api.routes import system
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
    lifespan=lifespan,
)
app.include_router(system.router, prefix=API_PREFIX)
