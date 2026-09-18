from fastapi import APIRouter

from app.schemas.system import HealthResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check: the process is up and serving requests.

    Deliberately does not touch the database. A readiness check (/system/ready) that
    also verifies PostgreSQL and storage comes with the database layer in Phase 2.
    """
    return HealthResponse(status="ok")
