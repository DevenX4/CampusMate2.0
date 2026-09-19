import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import current_schema_revision, expected_schema_revision, get_db
from app.schemas.system import HealthResponse, ReadinessResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: the process is up and serving requests. Deliberately does not touch
    the database, so a database outage does not make the process look dead."""
    return HealthResponse(status="ok")


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
