"""Run one ingestion job: PDF -> pages -> clean -> chunks -> enriched rows in document_chunks.

Transaction design:
- progress (current_stage) is committed as the job moves through the stages, so an admin
  can watch it;
- the result (old chunks deleted, new chunks inserted, version status, job 'completed') is
  ONE transaction: retrieval never sees half an index;
- on any error that transaction is rolled back and the failure is recorded separately.
  A failed NEW version never affects the version that is currently answering questions.
"""

import hashlib
import json
import logging
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.ingestion.chunking import chunk_pages
from app.ingestion.clean import clean_pages
from app.ingestion.enrich import chunk_source_type, find_entity_ids, official_page_context
from app.ingestion.extract import extract_pages, pages_in_scope
from app.models.documents import Document, DocumentChunk, DocumentVersion
from app.models.operations import IngestionJob
from app.services import audit, storage
from app.services.audit import RequestContext
from app.services.entities import known_entity_ids

logger = logging.getLogger(__name__)
SYSTEM = RequestContext(user_agent="ingestion-worker")


@dataclass
class JobResult:
    job_id: str
    status: str
    chunk_count: int | None = None
    error: str | None = None


class _Timer:
    """Records how long each stage takes (ms) and shows the current stage on the job row."""

    def __init__(self, db: Session, job: IngestionJob):
        self.db, self.job, self.timings = db, job, {}

    @contextmanager
    def stage(self, name: str):
        self.job.current_stage = name
        self.db.commit()  # progress is visible to the admin UI while the job runs
        start = time.perf_counter()
        yield
        self.timings[name] = round((time.perf_counter() - start) * 1000)


def claim_next_job(db: Session, lease_minutes: int) -> IngestionJob | None:
    """Take the oldest pending job. FOR UPDATE SKIP LOCKED means two workers can never take
    the same job. A job stuck in 'processing' past its lease belonged to a crashed worker
    and is taken again."""
    stale = func.now() - func.make_interval(0, 0, 0, 0, 0, lease_minutes)
    job = db.scalar(
        select(IngestionJob)
        .where(or_(IngestionJob.status == "pending",
                   and_(IngestionJob.status == "processing", IngestionJob.started_at < stale)))
        .order_by(IngestionJob.created_at).limit(1).with_for_update(skip_locked=True)
    )
    if job is None:
        db.rollback()
        return None
    job.status, job.current_stage = "processing", "claimed"
    job.attempts += 1
    job.started_at, job.finished_at, job.error_message, job.error_detail = datetime.now(UTC), None, None, None
    db.commit()
    return job


def build_chunks(db: Session, document: Document, version: DocumentVersion, path: Path,
                 max_chars: int, timer: _Timer, processed_dir: Path) -> list[DocumentChunk]:
    with timer.stage("extract"):
        pages = extract_pages(path, pages_in_scope(version.page_scope))
    with timer.stage("clean"):
        cleaned = clean_pages(pages)
    context = official_page_context(db, document.document_id, version.version_no)
    with timer.stage("chunk"):
        chunks = chunk_pages(cleaned.pages, max_chars, {page: c.title for page, c in context.items()})
    with timer.stage("enrich"):
        known = known_entity_ids(db)
        rows = []
        for index, chunk in enumerate(chunks):
            entity_ids = find_entity_ids(chunk.text, known)
            source_type, labels = chunk_source_type(chunk.text, document.source_type)
            pages_ctx = [context[p] for p in range(chunk.page_start, chunk.page_end + 1) if p in context]
            rows.append(DocumentChunk(
                document_id=document.document_id, version_no=version.version_no, chunk_index=index,
                text=chunk.text, content_sha256=hashlib.sha256(chunk.text.encode()).hexdigest(),
                page_start=chunk.page_start, page_end=chunk.page_end, section=chunk.section,
                source_type=source_type, entity_ids=entity_ids,
                metadata_={
                    "title": document.title,
                    "document_type": document.document_type,
                    "department_id": document.department_id,
                    "academic_year": version.academic_year,
                    "program_ids": sorted({c.program_id for c in pages_ctx}
                                          | {e for e in entity_ids if e.startswith("PROG-")}),
                    "semester_ids": sorted({c.semester_id for c in pages_ctx}
                                           | {e for e in entity_ids if e.startswith("SEM-")}),
                    "source_labels": labels,
                },
            ))
    # A readable copy of what was extracted, for debugging (storage/processed/<doc>/v<n>.json).
    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / f"v{version.version_no}.json").write_text(json.dumps({
        "document_id": document.document_id, "version_no": version.version_no,
        "removed_boilerplate": cleaned.removed_boilerplate, "repaired_strings": cleaned.repaired_strings,
        "pages": [{"page": p.number, "lines": p.lines} for p in cleaned.pages],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def _activate_if_newer(db: Session, document: Document, version: DocumentVersion) -> int | None:
    """After a successful ingest, a NEWER version replaces the answering one automatically
    (the old one is kept as 'superseded' for rollback). Returns the replaced version number."""
    active = db.scalar(select(DocumentVersion).where(
        DocumentVersion.document_id == document.document_id, DocumentVersion.status == "active"))
    if document.status == "deleted" or (active is not None and active.version_no > version.version_no):
        return None
    if active is not None:
        active.status = "superseded"
        db.flush()
    version.status, version.activated_at = "active", datetime.now(UTC)
    return active.version_no if active else None


def run_job(db: Session, job: IngestionJob, storage_root: Path, max_chars: int) -> JobResult:
    job_uuid, job_id = job.id, str(job.id)
    timer = _Timer(db, job)
    try:
        document = db.get(Document, job.document_id)
        version = db.get(DocumentVersion, (job.document_id, job.version_no))
        path = storage.resolve(storage_root, version.storage_key)
        rows = build_chunks(db, document, version, path, max_chars, timer,
                            storage_root / "processed" / document.document_id)
        with timer.stage("store"):
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == job.document_id,
                                                   DocumentChunk.version_no == job.version_no))
            db.add_all(rows)
            replaced = None
            if job.job_type == "ingest":
                version.status = "ready"
                replaced = _activate_if_newer(db, document, version)
        job.status, job.current_stage, job.finished_at = "completed", "done", datetime.now(UTC)
        job.chunk_count, job.stage_timings = len(rows), timer.timings
        audit.record(db, "ingestion.completed", actor_id=None, context=SYSTEM, entity_type="document",
                     entity_id=job.document_id,
                     details={"job_id": job_id, "version_no": job.version_no, "chunks": len(rows),
                              "activated": version.status == "active", "replaced_version_no": replaced})
        db.commit()
        logger.info("Job %s: %s v%s -> %d chunks %s", job_id, job.document_id, job.version_no, len(rows), timer.timings)
        return JobResult(job_id, "completed", len(rows))
    except Exception as exc:
        db.rollback()
        return _record_failure(db, job_uuid, exc, timer)


def _record_failure(db: Session, job_uuid, exc: Exception, timer: _Timer) -> JobResult:
    job_id = str(job_uuid)
    logger.exception("Job %s failed", job_id)
    job = db.get(IngestionJob, job_uuid)
    stage = job.current_stage
    job.status, job.finished_at = "failed", datetime.now(UTC)
    job.error_message = f"{type(exc).__name__}: {exc}"[:500]
    job.error_detail = {"stage": stage, "type": type(exc).__name__,
                        "trace": traceback.format_exc(limit=5)[-2000:]}
    job.stage_timings = timer.timings
    if job.job_type == "ingest":
        db.get(DocumentVersion, (job.document_id, job.version_no)).status = "failed"
    audit.record(db, "ingestion.failed", actor_id=None, context=SYSTEM, entity_type="document",
                 entity_id=job.document_id, details={"job_id": job_id, "stage": stage,
                                                     "error": job.error_message})
    db.commit()
    return JobResult(job_id, "failed", error=job.error_message)


def process_next(db: Session, storage_root: Path, *, max_chars: int, lease_minutes: int) -> JobResult | None:
    job = claim_next_job(db, lease_minutes)
    return None if job is None else run_job(db, job, storage_root, max_chars)
