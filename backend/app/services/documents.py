"""Document registry: uploads, versions, activation, lifecycle and reindex requests.

Only an ACTIVE version of an ACTIVE document is ever used for answers (from Phase 7 on).
Every change is audited in the same transaction, and every upload or reindex queues a
durable ingestion job.
"""

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.documents import Document, DocumentChunk, DocumentEntity, DocumentVersion
from app.models.operations import IngestionJob
from app.models.organization import Department
from app.schemas.common import Page
from app.schemas.documents import (
    DocumentDetail, DocumentForm, DocumentStats, DocumentSummary, JobOut, VersionForm, VersionOut,
)
from app.services import audit, storage
from app.services.audit import RequestContext
from app.services.errors import ConflictError, NotFoundError, UploadRejected
from app.services.helpers import build, contains
from app.services.pdf import inspect_pdf

# Which document-level actions are allowed from which status.
TRANSITIONS = {
    "activate": {"inactive", "archived"},
    "deactivate": {"active"},
    "archive": {"active", "inactive"},
    "delete": {"active", "inactive", "archived"},  # soft delete; "deleted" is final
}
RESULT_STATUS = {"activate": "active", "deactivate": "inactive", "archive": "archived", "delete": "deleted"}
ACTIVATABLE_VERSION = {"ready", "superseded"}  # ingested; or previously active (rollback)
OPEN_JOB = ("pending", "processing")


# --- reading ------------------------------------------------------------------------------

def _get_document(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document", document_id)
    return document


def _active_version(db: Session, document_id: str) -> DocumentVersion | None:
    return db.scalar(select(DocumentVersion).where(
        DocumentVersion.document_id == document_id, DocumentVersion.status == "active"))


def _summary(db: Session, document: Document) -> DocumentSummary:
    active = _active_version(db, document.document_id)
    latest = db.scalar(select(func.max(DocumentVersion.version_no))
                       .where(DocumentVersion.document_id == document.document_id))
    return build(DocumentSummary, document,
                 active_version=VersionOut.model_validate(active) if active else None,
                 latest_version_no=latest)


def list_documents(db: Session, *, q: str | None, document_type: str | None, source_type: str | None,
                   status: str | None, department_id: str | None, limit: int, offset: int) -> Page[DocumentSummary]:
    query = select(Document)
    if q:
        query = query.where(or_(contains(Document.title, q), contains(Document.document_id, q)))
    for column, value in ((Document.document_type, document_type), (Document.source_type, source_type),
                          (Document.department_id, department_id)):
        if value:
            query = query.where(column == value)
    # Deleted documents are hidden unless explicitly asked for.
    query = query.where(Document.status == status) if status else query.where(Document.status != "deleted")
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    documents = db.scalars(query.order_by(Document.updated_at.desc(), Document.document_id)
                           .limit(limit).offset(offset)).all()
    return Page(items=[_summary(db, d) for d in documents], total=total, limit=limit, offset=offset)


def get_document(db: Session, document_id: str) -> DocumentDetail:
    document = _get_document(db, document_id)
    summary = _summary(db, document)
    versions = db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document_id)
                          .order_by(DocumentVersion.version_no.desc())).all()
    jobs = db.scalars(select(IngestionJob).where(IngestionJob.document_id == document_id)
                      .order_by(IngestionJob.created_at.desc()).limit(10)).all()
    active_no = summary.active_version.version_no if summary.active_version else None
    entity_count = db.scalar(select(func.count()).select_from(DocumentEntity).where(
        DocumentEntity.document_id == document_id, DocumentEntity.version_no == active_no)) or 0
    return DocumentDetail(**summary.model_dump(), versions=[VersionOut.model_validate(v) for v in versions],
                          recent_jobs=[JobOut.model_validate(j) for j in jobs], entity_count=entity_count)


def list_versions(db: Session, document_id: str) -> list[VersionOut]:
    return get_document(db, document_id).versions


def stats(db: Session) -> DocumentStats:
    active_docs = select(Document.document_id).where(Document.status == "active")
    return DocumentStats(
        active_documents=db.scalar(select(func.count()).select_from(active_docs.subquery())),
        total_documents=db.scalar(select(func.count()).select_from(Document).where(Document.status != "deleted")),
        total_chunks=db.scalar(
            select(func.count()).select_from(DocumentChunk)
            .join(DocumentVersion, (DocumentVersion.document_id == DocumentChunk.document_id)
                  & (DocumentVersion.version_no == DocumentChunk.version_no))
            .where(DocumentVersion.status == "active", DocumentChunk.document_id.in_(active_docs))),
        pending_jobs=db.scalar(select(func.count()).select_from(IngestionJob).where(IngestionJob.status.in_(OPEN_JOB))),
        failed_jobs=db.scalar(select(func.count()).select_from(IngestionJob).where(IngestionJob.status == "failed")),
        last_updated=db.scalar(select(func.max(Document.updated_at))),
    )


def version_file(db: Session, storage_root: Path, document_id: str, version_no: int) -> tuple[Path, DocumentVersion]:
    version = db.get(DocumentVersion, (document_id, version_no))
    if version is None:
        raise NotFoundError("Document version", f"{document_id} v{version_no}")
    path = storage.resolve(storage_root, version.storage_key)
    if not path.is_file():
        raise NotFoundError("Stored file", version.storage_key)
    return path, version


# --- uploads --------------------------------------------------------------------------------

def safe_filename(name: str | None) -> str:
    """Keep only a harmless display name: no directories, no control characters."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()[:200]
    return base or "upload.pdf"


def check_upload(received: storage.ReceivedFile, filename: str, content_type: str | None) -> int:
    """Validate an uploaded file; returns its page count. Name, declared type AND content are checked."""
    if not filename.lower().endswith(".pdf"):
        raise UploadRejected("unsupported_type", "Only PDF files (.pdf) are accepted")
    if content_type not in ("application/pdf", "application/x-pdf"):
        raise UploadRejected("unsupported_type", f"Declared content type {content_type!r} is not a PDF")
    return inspect_pdf(received.temp_path)


def _ensure_new_content(db: Session, sha256: str) -> None:
    existing = db.scalar(select(DocumentVersion).where(DocumentVersion.sha256 == sha256))
    if existing is not None:
        raise ConflictError(f"This exact file is already registered as {existing.document_id} "
                            f"version {existing.version_no}; nothing to re-process")


def _new_version(document_id: str, version_no: int, received: storage.ReceivedFile, key: str,
                 filename: str, pages: int, form: VersionForm, actor: User) -> DocumentVersion:
    if form.effective_from and form.effective_to and form.effective_to < form.effective_from:
        raise UploadRejected("invalid", "effective_to is before effective_from")
    return DocumentVersion(
        document_id=document_id, version_no=version_no, sha256=received.sha256, storage_key=key,
        original_filename=filename, mime_type="application/pdf", size_bytes=received.size_bytes,
        page_count=pages, version_label=form.version_label, academic_year=form.academic_year,
        effective_from=form.effective_from, effective_to=form.effective_to, notes=form.notes,
        status="pending", uploaded_by=actor.id,
    )


def _queue_job(db: Session, document_id: str, version_no: int, job_type: str, actor: User) -> None:
    db.add(IngestionJob(document_id=document_id, version_no=version_no, job_type=job_type,
                        requested_by=actor.id))


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:  # e.g. the same file uploaded twice at the same moment
        db.rollback()
        raise ConflictError("The upload conflicts with an existing document or version") from exc


def create_document(db: Session, received: storage.ReceivedFile, filename: str, content_type: str | None,
                    form: DocumentForm, *, storage_root: Path, actor: User, context: RequestContext) -> DocumentDetail:
    try:
        pages = check_upload(received, filename, content_type)
        _ensure_new_content(db, received.sha256)
        if form.department_id and db.get(Department, form.department_id) is None:
            raise NotFoundError("Department", form.department_id)
    except Exception:
        received.discard()
        raise
    key = storage.accept_upload(storage_root, received, ".pdf")

    document_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"
    db.add(Document(document_id=document_id, title=form.title, document_type=form.document_type,
                    source_type=form.source_type, department_id=form.department_id,
                    status="active", created_by=actor.id))
    db.flush()
    db.add(_new_version(document_id, 1, received, key, filename, pages, form, actor))
    db.flush()
    _queue_job(db, document_id, 1, "ingest", actor)
    audit.record(db, "document.upload", actor_id=actor.id, context=context, entity_type="document",
                 entity_id=document_id, details={"version_no": 1, "sha256": received.sha256,
                                                 "filename": filename, "source_type": form.source_type})
    _commit(db)
    return get_document(db, document_id)


def add_version(db: Session, document_id: str, received: storage.ReceivedFile, filename: str,
                content_type: str | None, form: VersionForm, *, storage_root: Path, actor: User,
                context: RequestContext) -> DocumentDetail:
    """Replacement = upload a new version. The current active version stays active (and
    answerable) until the new one has been ingested and activated."""
    try:
        document = _get_document(db, document_id)
        if document.status in ("deleted", "archived"):
            raise ConflictError(f"Document {document_id} is {document.status}; restore it first")
        pages = check_upload(received, filename, content_type)
        _ensure_new_content(db, received.sha256)
    except Exception:
        received.discard()
        raise
    key = storage.accept_upload(storage_root, received, ".pdf")

    version_no = (db.scalar(select(func.max(DocumentVersion.version_no))
                            .where(DocumentVersion.document_id == document_id)) or 0) + 1
    db.add(_new_version(document_id, version_no, received, key, filename, pages, form, actor))
    db.flush()
    _queue_job(db, document_id, version_no, "ingest", actor)
    document.updated_at = func.now()
    audit.record(db, "document.version_upload", actor_id=actor.id, context=context, entity_type="document",
                 entity_id=document_id, details={"version_no": version_no, "sha256": received.sha256,
                                                 "filename": filename})
    _commit(db)
    return get_document(db, document_id)


# --- lifecycle ------------------------------------------------------------------------------

def activate_version(db: Session, document_id: str, version_no: int, *, actor: User,
                     context: RequestContext) -> DocumentDetail:
    """Make one version the one used for answers; the previous active version becomes
    'superseded' (kept, so it can be re-activated later as a rollback)."""
    document = _get_document(db, document_id)
    if document.status == "deleted":
        raise ConflictError(f"Document {document_id} is deleted")
    version = db.get(DocumentVersion, (document_id, version_no))
    if version is None:
        raise NotFoundError("Document version", f"{document_id} v{version_no}")
    if version.status == "active":
        return get_document(db, document_id)  # already active: nothing to do
    if version.status not in ACTIVATABLE_VERSION:
        raise ConflictError(f"Version {version_no} is '{version.status}'; only ingested ('ready') or "
                            f"previously active ('superseded') versions can be activated")

    previous = _active_version(db, document_id)
    if previous is not None:
        previous.status = "superseded"
        db.flush()  # free the "one active version" slot before taking it
    version.status = "active"
    version.activated_at = datetime.now(UTC)
    document.updated_at = func.now()
    audit.record(db, "document.version_activate", actor_id=actor.id, context=context,
                 entity_type="document", entity_id=document_id,
                 details={"version_no": version_no,
                          "previous_version_no": previous.version_no if previous else None})
    db.commit()
    return get_document(db, document_id)


def change_status(db: Session, document_id: str, action: str, *, actor: User,
                  context: RequestContext) -> DocumentDetail:
    document = _get_document(db, document_id)
    if document.status not in TRANSITIONS[action]:
        raise ConflictError(f"Cannot {action} a document that is '{document.status}'")
    previous = document.status
    document.status = RESULT_STATUS[action]
    audit.record(db, f"document.{action}", actor_id=actor.id, context=context, entity_type="document",
                 entity_id=document_id, details={"from": previous, "to": document.status})
    db.commit()
    return get_document(db, document_id)


def request_reindex(db: Session, document_id: str, *, actor: User, context: RequestContext) -> DocumentDetail:
    document = _get_document(db, document_id)
    if document.status == "deleted":
        raise ConflictError(f"Document {document_id} is deleted")
    active = _active_version(db, document_id)
    if active is None:
        raise ConflictError(f"Document {document_id} has no active version to re-index")
    open_job = db.scalar(select(IngestionJob).where(
        IngestionJob.document_id == document_id, IngestionJob.version_no == active.version_no,
        IngestionJob.status.in_(OPEN_JOB)))
    if open_job is not None:
        raise ConflictError(f"Version {active.version_no} already has a {open_job.status} job ({open_job.id})")
    _queue_job(db, document_id, active.version_no, "reindex", actor)
    audit.record(db, "document.reindex", actor_id=actor.id, context=context, entity_type="document",
                 entity_id=document_id, details={"version_no": active.version_no})
    db.commit()
    return get_document(db, document_id)
