"""FastAPI application — CampusMate AI Backend API."""

import logging
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.middleware import BodySizeLimit, add_request_id_middleware, add_security_headers_middleware
from app.api.routes import (
    audit, auth, chat, chat_bypass, content, courses, departments, documents, faculty,
    ingestion, knowledge, programs, routing, search, system, users,
)
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("campusmate")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s API server", settings.app_name)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=version("campusmate-backend"),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BodySizeLimit, max_bytes=settings.max_body_kb * 1024)
add_request_id_middleware(app)
add_security_headers_middleware(app)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "CampusMate Hybrid RAG Engine",
        "version": "2.0",
        "endpoints": {
            "docs": "/docs",
            "chat_hybrid": "/api/v1/chat/hybrid",
            "chat_bypass": "/api/v1/chat/bypass"
        }
    }

# Include all API routers
for router_module in [
    system, auth, chat, chat_bypass, users, audit, departments, faculty, courses,
    programs, content, documents, routing, ingestion, knowledge, search,
]:
    app.include_router(router_module.router, prefix=API_PREFIX)
