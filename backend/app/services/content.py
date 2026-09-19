"""Policies, notices, the academic calendar, and the documents answers can come from."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import CalendarEvent, Notice, Policy, calendar_event_semesters
from app.models.documents import Document, DocumentChunk, DocumentVersion
from app.schemas.content import CalendarEventOut, KnowledgeSource, NoticeOut, PolicyOut
from app.services.helpers import build


def list_policies(db: Session) -> list[PolicyOut]:
    return [PolicyOut.model_validate(p) for p in db.scalars(select(Policy).order_by(Policy.policy_number))]


def list_notices(db: Session, limit: int, today: date | None = None) -> list[NoticeOut]:
    today = today or date.today()
    superseded = set(db.scalars(select(Notice.supersedes_notice_id).where(Notice.supersedes_notice_id.is_not(None))))
    notices = db.scalars(select(Notice).order_by(Notice.notice_date.desc(), Notice.notice_id).limit(limit))
    return [build(NoticeOut, n, is_current=n.notice_id not in superseded
                  and (n.effective_date is None or n.effective_date <= today)
                  and (n.expiry_date is None or today <= n.expiry_date)) for n in notices]


def list_calendar(db: Session, semester_id: str | None) -> list[CalendarEventOut]:
    links = db.execute(select(calendar_event_semesters.c.event_id, calendar_event_semesters.c.semester_id)).all()
    semesters_of: dict[str, list[str]] = {}
    for event_id, sem_id in links:
        semesters_of.setdefault(event_id, []).append(sem_id)
    query = select(CalendarEvent).order_by(CalendarEvent.start_date, CalendarEvent.event_id)
    if semester_id:
        query = query.where(CalendarEvent.event_id.in_([e for e, s in links if s == semester_id]))
    return [build(CalendarEventOut, e, semester_ids=sorted(semesters_of.get(e.event_id, [])))
            for e in db.scalars(query)]


def knowledge_sources(db: Session) -> list[KnowledgeSource]:
    """The documents answers can come from right now: active versions of active documents."""
    chunks = (select(DocumentChunk.document_id, DocumentChunk.version_no, func.count().label("n"))
              .group_by(DocumentChunk.document_id, DocumentChunk.version_no).subquery())
    rows = db.execute(
        select(Document, DocumentVersion, func.coalesce(chunks.c.n, 0))
        .join(DocumentVersion, (DocumentVersion.document_id == Document.document_id) & (DocumentVersion.status == "active"))
        .outerjoin(chunks, (chunks.c.document_id == Document.document_id) & (chunks.c.version_no == DocumentVersion.version_no))
        .where(Document.status == "active")
        .order_by(Document.source_type, Document.title)
    ).all()
    return [KnowledgeSource(document_id=d.document_id, title=d.title, document_type=d.document_type,
                            source_type=d.source_type, version_no=v.version_no, academic_year=v.academic_year,
                            chunks=n) for d, v, n in rows]
