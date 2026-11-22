"""Policies, notices and the academic calendar (read-only). All of them are labelled with their
trust level: in the current dataset they are synthetic demo data."""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import FromORM, Provenance


class PolicyOut(FromORM):
    policy_id: str
    policy_number: str
    title: str
    category: str | None
    summary: str | None
    clauses: list[str] | None
    effective_from: date | None
    effective_to: date | None
    status: str
    academic_year: str | None
    provenance: Provenance


class NoticeOut(FromORM):
    notice_id: str
    title: str
    notice_date: date
    category: str | None
    target_audience: list[str] | None
    content: str
    effective_date: date | None
    expiry_date: date | None
    academic_year: str | None
    is_current: bool = Field(description="Computed: in force today and not superseded by a newer notice")
    provenance: Provenance


class CalendarEventOut(FromORM):
    event_id: str
    title: str
    event_type: str | None
    start_date: date
    end_date: date
    term: str | None
    academic_year: str | None
    semester_ids: list[str]
    provenance: Provenance


class KnowledgeSource(BaseModel):
    document_id: str
    title: str
    document_type: str
    source_type: str
    version_no: int
    academic_year: str | None
    chunks: int
