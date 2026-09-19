"""Request and response shapes for document management."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import FromORM

DocumentType = Literal[
    # types present in the dataset registry
    "official_structured_syllabus", "official_certified_course_list", "department_profile",
    "faculty_directory", "programs_and_curriculum", "course_catalog", "laboratories",
    "facilities", "policies", "academic_calendar", "notices", "student_services_faq",
    # further categories offered by the admin upload form
    "syllabus", "examination", "handbook", "other",
]
AcademicYear = Field(default=None, pattern=r"^\d{4}-\d{4}$", examples=["2026-2027"])


class VersionForm(BaseModel):
    """Metadata sent with every uploaded file (multipart form fields)."""

    version_label: str | None = Field(default=None, max_length=200)
    academic_year: str | None = AcademicYear
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DocumentForm(VersionForm):
    """Metadata for a brand-new document. `source_type` must be declared explicitly: the admin
    decides whether a file is an official Ganpat University document or demo data."""

    title: str = Field(min_length=3, max_length=300)
    document_type: DocumentType
    source_type: Literal["official", "synthetic"]
    department_id: str | None = None


class VersionOut(FromORM):
    version_no: int
    status: str
    sha256: str
    original_filename: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    page_scope: dict | None
    version_label: str | None
    academic_year: str | None
    effective_from: date | None
    effective_to: date | None
    notes: str | None
    uploaded_by: uuid.UUID | None
    created_at: datetime
    activated_at: datetime | None


class JobOut(FromORM):
    id: uuid.UUID
    version_no: int
    job_type: str
    status: str
    current_stage: str | None
    attempts: int
    error_message: str | None
    chunk_count: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class DocumentSummary(FromORM):
    document_id: str
    title: str
    document_type: str
    source_type: str
    department_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    active_version: VersionOut | None = None
    latest_version_no: int | None = None


class DocumentDetail(DocumentSummary):
    versions: list[VersionOut]
    recent_jobs: list[JobOut]
    entity_count: int = Field(description="Entities described by the active version (from the registry)")


class DocumentStats(BaseModel):
    """The numbers on the admin dashboard cards."""

    active_documents: int
    total_documents: int = Field(description="All documents except deleted ones")
    total_chunks: int = Field(description="Indexed chunks of active versions of active documents")
    pending_jobs: int = Field(description="Ingestion jobs pending or in progress")
    failed_jobs: int
    last_updated: datetime | None


DocumentAction = Literal["activate", "deactivate", "archive", "delete"]
