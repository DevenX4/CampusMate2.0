"""Documents, their versions, and the text chunks extracted from each version.

    Document DOC-FAQ-001
      ├── version 1  (superseded)
      └── version 2  (active)   <- the only version retrieval uses
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, Integer, Text,
    UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import SOURCE_TYPES, Base, TimestampMixin, in_list

DOCUMENT_SOURCE_TYPES = ("official", "synthetic")  # a whole file is one or the other
DOCUMENT_STATUSES = ("active", "inactive", "archived", "deleted")  # deleted = soft delete
# pending: stored, not yet ingested | ready: ingested, not active | active: used by retrieval
VERSION_STATUSES = ("pending", "ready", "active", "superseded", "failed")


class Document(TimestampMixin, Base):
    """The stable identity of a document, independent of any particular file version."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(in_list("source_type", DOCUMENT_SOURCE_TYPES), name="source_type"),
        CheckConstraint(in_list("status", DOCUMENT_STATUSES), name="status"),
    )

    document_id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    document_type: Mapped[str]
    source_type: Mapped[str]
    # documents -> departments -> document_versions (provenance) -> documents is a cycle,
    # so this constraint is added after table creation and checked at COMMIT.
    department_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "departments.department_id", use_alter=True, deferrable=True, initially="DEFERRED"
        )
    )
    source_url: Mapped[str | None]
    status: Mapped[str] = mapped_column(server_default="active")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", order_by="DocumentVersion.version_no"
    )


class DocumentVersion(TimestampMixin, Base):
    """One uploaded file. Identified by (document_id, version_no), e.g. (DOC-FAQ-001, 2)."""

    __tablename__ = "document_versions"
    __table_args__ = (
        CheckConstraint("version_no > 0", name="version_no_positive"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("page_count IS NULL OR page_count > 0", name="page_count_positive"),
        CheckConstraint(in_list("status", VERSION_STATUSES), name="status"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="effective_range",
        ),
        # At most ONE active version per document: a partial unique index only
        # covers rows WHERE status = 'active'.
        Index(
            "uq_document_versions_one_active", "document_id",
            unique=True, postgresql_where=text("status = 'active'"),
        ),
    )

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.document_id"), primary_key=True
    )
    version_no: Mapped[int] = mapped_column(primary_key=True)
    # Identical bytes are never stored twice, even under another document: duplicate detection.
    sha256: Mapped[str] = mapped_column(unique=True)
    # Where the bytes live, relative to the storage root. Content-addressed by sha256.
    storage_key: Mapped[str] = mapped_column(unique=True)
    original_filename: Mapped[str]
    mime_type: Mapped[str]
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    page_count: Mapped[int | None]
    # Which pages matter, e.g. {"PROG-BTECH-IT-001": [10, ..., 18]} for the university-wide syllabus.
    page_scope: Mapped[dict | None]
    version_label: Mapped[str | None]  # as the source names it, e.g. "Syllabus Details dated 28/09/2022"
    academic_year: Mapped[str | None]
    effective_from: Mapped[date | None]  # NULL when the source gives no exact date
    effective_to: Mapped[date | None]
    status: Mapped[str] = mapped_column(server_default="pending")
    notes: Mapped[str | None]
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    activated_at: Mapped[datetime | None]

    document: Mapped[Document] = relationship(back_populates="versions")


class DocumentEntity(Base):
    """Which entities a document version describes, and on which pages.
    Used to answer "what is affected if this document is replaced?"."""

    __tablename__ = "document_entities"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "version_no"],
            ["document_versions.document_id", "document_versions.version_no"],
            ondelete="CASCADE",
        ),
    )

    document_id: Mapped[str] = mapped_column(primary_key=True)
    version_no: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[str] = mapped_column(primary_key=True)
    pages: Mapped[list[int]] = mapped_column(ARRAY(Integer), server_default="{}")


class DocumentChunk(Base):
    """A piece of extracted text: the canonical input for vector and BM25 indexes (Phase 7+)."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "version_no"],
            ["document_versions.document_id", "document_versions.version_no"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("document_id", "version_no", "chunk_index"),
        # Tracked per chunk: a synthetic PDF can still contain official facts.
        CheckConstraint(in_list("source_type", SOURCE_TYPES), name="source_type"),
        CheckConstraint("chunk_index >= 0", name="chunk_index_non_negative"),
        CheckConstraint(
            "page_end IS NULL OR page_start IS NULL OR page_end >= page_start", name="page_range"
        ),
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid()
    )
    document_id: Mapped[str]
    version_no: Mapped[int]
    chunk_index: Mapped[int]
    text: Mapped[str]
    content_sha256: Mapped[str]
    page_start: Mapped[int | None]
    page_end: Mapped[int | None]
    section: Mapped[str | None]
    source_type: Mapped[str]
    entity_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    # "metadata" is reserved by SQLAlchemy models, so the attribute has a trailing underscore.
    metadata_: Mapped[dict] = mapped_column("metadata", server_default=text("'{}'::jsonb"))
    token_count: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
