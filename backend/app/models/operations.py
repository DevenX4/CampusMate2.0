"""Operational records: durable ingestion jobs and the append-only audit log."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, ForeignKey, ForeignKeyConstraint, Identity, Index, func, text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, in_list

JOB_TYPES = ("ingest", "reindex", "purge")
JOB_STATUSES = ("pending", "processing", "completed", "failed")


class IngestionJob(Base):
    """One unit of background work on one document version. Stored in PostgreSQL so a job
    survives a server restart (unlike FastAPI BackgroundTasks, which live in memory)."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "version_no"],
            ["document_versions.document_id", "document_versions.version_no"],
        ),
        CheckConstraint(in_list("job_type", JOB_TYPES), name="job_type"),
        CheckConstraint(in_list("status", JOB_STATUSES), name="status"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="time_order",
        ),
        # The worker's query: "oldest pending job first".
        Index("ix_ingestion_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    document_id: Mapped[str]
    version_no: Mapped[int]
    job_type: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="pending")
    current_stage: Mapped[str | None]
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    error_message: Mapped[str | None]
    error_detail: Mapped[dict | None]
    stage_timings: Mapped[dict] = mapped_column(server_default=text("'{}'::jsonb"))  # stage -> ms
    chunk_count: Mapped[int | None]
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    """Who did what, when. Append-only: a database trigger (see the initial migration)
    rejects UPDATE, DELETE and TRUNCATE, so history cannot be rewritten through the app.
    Users with audit history are deactivated, never deleted (the FK has no cascade)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_occurred_at", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str]  # e.g. "document.upload", "document.deactivate"
    entity_type: Mapped[str | None]
    entity_id: Mapped[str | None]
    request_id: Mapped[str | None]
    ip_address: Mapped[str | None] = mapped_column(INET)
    details: Mapped[dict] = mapped_column(server_default=text("'{}'::jsonb"))
