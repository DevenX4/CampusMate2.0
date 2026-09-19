import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import AUTH_ERRORS, NOT_FOUND, Context, DbSession, Limit, Offset, require
from app.models.auth import User
from app.schemas.common import ErrorResponse, Page
from app.schemas.ingestion import IngestionJobOut
from app.services import ingestion_jobs

router = APIRouter(prefix="/ingestion/jobs", tags=["ingestion"], responses=AUTH_ERRORS)
Manager = Annotated[User, Depends(require("ingestion:manage"))]


@router.get("", response_model=Page[IngestionJobOut])
def list_jobs(
    db: DbSession, admin: Manager, document_id: str | None = None,
    status_filter: Annotated[Literal["pending", "processing", "completed", "failed"] | None,
                             Query(alias="status")] = None,
    limit: Limit = 20, offset: Offset = 0,
):
    """Newest first. Run the worker with: python -m app.ingestion worker"""
    return ingestion_jobs.list_jobs(db, status=status_filter, document_id=document_id, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=IngestionJobOut, responses=NOT_FOUND)
def get_job(job_id: uuid.UUID, db: DbSession, admin: Manager):
    """Includes the current stage, per-stage timings (ms) and, for failures, the error."""
    return ingestion_jobs.get_job(db, job_id)


@router.post("/{job_id}/retry", response_model=IngestionJobOut,
             responses={**NOT_FOUND, 409: {"model": ErrorResponse, "description": "Job is not failed"}})
def retry_job(job_id: uuid.UUID, db: DbSession, admin: Manager, context: Context):
    return ingestion_jobs.retry_job(db, job_id, actor=admin, context=context)
