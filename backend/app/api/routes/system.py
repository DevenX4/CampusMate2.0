import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from importlib.metadata import version

from app.api.deps import AUTH_ERRORS, CurrentUser
from app.core.config import get_settings
from app.core.db import current_schema_revision, expected_schema_revision, get_db
from app.schemas.system import HealthResponse, ReadinessResponse, SystemInfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: the process is up and serving requests. Deliberately does not touch
    the database, so a database outage does not make the process look dead."""
    return HealthResponse(status="ok")


@router.get("/info", response_model=SystemInfo, responses=AUTH_ERRORS)
def info(user: CurrentUser) -> SystemInfo:
    """The versions and configuration of this installation (logged-in users). No secrets."""
    s = get_settings()
    return SystemInfo(
        version=version("campusmate-backend"), environment=s.app_env,
        generation_provider=s.generation_provider,
        generation_model=s.generation_model or "extractive-v1 (no model)",
        embedding_model=s.embedding_model,
        vector_store="Chroma server" if s.chroma_url else "Chroma (embedded)",
        vector_store_version=version("chromadb"), reranker_model=s.reranker_model,
        ingestion_in_api=s.ingestion_in_api,
        limits={"login_max_failures": s.login_max_failures, "login_window_minutes": s.login_window_minutes,
                "chat_questions_per_minute": s.chat_questions_per_minute, "max_upload_mb": s.max_upload_mb,
                "session_ttl_hours": s.session_ttl_hours})


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def ready(response: Response, db: Annotated[Session, Depends(get_db)]) -> ReadinessResponse:
    """Readiness: PostgreSQL is reachable AND its schema is at the migration this code expects.
    Returns 503 otherwise, e.g. when someone forgot to run `alembic upgrade head`."""
    expected = expected_schema_revision()
    try:
        current = current_schema_revision(db)
    except SQLAlchemyError:
        logger.exception("Readiness check failed: database unreachable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready", database="unreachable",
            schema_revision=None, expected_revision=expected,
        )

    is_ready = current == expected
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready", database="ok",
        schema_revision=current, expected_revision=expected,
    )
