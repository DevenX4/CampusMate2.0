"""Viewing and retrying ingestion jobs (the worker itself is app/ingestion)."""

import uuid

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.documents import Document, DocumentChunk, DocumentVersion
from app.models.operations import IngestionJob
from app.schemas.common import Page
from app.schemas.ingestion import IngestionJobOut
from app.services import audit
from app.services.audit import RequestContext
from app.services.errors import ConflictError, NotFoundError
from app.services.helpers import paginate


def list_jobs(db: Session, *, status: str | None, document_id: str | None,
              limit: int, offset: int) -> Page[IngestionJobOut]:
    query = select(IngestionJob).order_by(IngestionJob.created_at.desc())
    if status:
        query = query.where(IngestionJob.status == status)
    if document_id:
        query = query.where(IngestionJob.document_id == document_id)
    return paginate(db, query, IngestionJobOut, limit, offset)


def get_job(db: Session, job_id: uuid.UUID) -> IngestionJobOut:
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise NotFoundError("Ingestion job", str(job_id))
    return IngestionJobOut.model_validate(job)


def retry_job(db: Session, job_id: uuid.UUID, *, actor: User, context: RequestContext) -> IngestionJobOut:
    """Put a failed job back in the queue; the worker picks it up again."""
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise NotFoundError("Ingestion job", str(job_id))
    if job.status != "failed":
        raise ConflictError(f"Only failed jobs can be retried; this one is '{job.status}'")
    job.status, job.current_stage, job.error_message, job.error_detail = "pending", None, None, None
    job.started_at = job.finished_at = None
    audit.record(db, "ingestion.retry", actor_id=actor.id, context=context, entity_type="document",
                 entity_id=job.document_id, details={"job_id": str(job.id), "attempts_so_far": job.attempts})
    db.commit()
    return IngestionJobOut.model_validate(job)


def queue_missing(db: Session) -> int:
    """Queue a 'reindex' job for every active version of a non-deleted document that has no
    chunks and no job already waiting (e.g. the documents registered by the dataset seed)."""
    has_chunks = exists().where(DocumentChunk.document_id == DocumentVersion.document_id,
                                DocumentChunk.version_no == DocumentVersion.version_no)
    has_open_job = exists().where(IngestionJob.document_id == DocumentVersion.document_id,
                                  IngestionJob.version_no == DocumentVersion.version_no,
                                  IngestionJob.status.in_(("pending", "processing")))
    versions = db.scalars(
        select(DocumentVersion).join(Document)
        .where(DocumentVersion.status == "active", Document.status != "deleted", ~has_chunks, ~has_open_job)
        .order_by(DocumentVersion.document_id)
    ).all()
    for version in versions:
        db.add(IngestionJob(document_id=version.document_id, version_no=version.version_no, job_type="reindex"))
    db.commit()
    return len(versions)
