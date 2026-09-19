"""Chat history and feedback."""

import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.chat.pipeline import ChatAnswer
from app.models.chat import ChatFeedback, ChatQuery
from app.services.errors import NotFoundError


def source_records(answer: ChatAnswer) -> list[dict]:
    """What each [ref] pointed at, and whether the answer cited it."""
    cited = set(answer.grounding.cited)
    return [{"ref": ref, "kind": e.kind, "source_type": e.source_type, "document_id": e.citation.document_id,
             "version_no": e.citation.version_no, "page_start": e.citation.page_start,
             "page_end": e.citation.page_end, "entity_ids": e.entity_ids[:10], "cited": ref in cited}
            for ref, e in answer.context.evidence.items()]


def log_answer(db: Session, user_id: uuid.UUID | None, answer: ChatAnswer) -> ChatQuery:
    report = answer.grounding
    row = ChatQuery(user_id=user_id, question=answer.question, route=answer.route, intents=answer.intents,
                    answer=answer.answer, answer_type=answer.answer_type, provider=answer.provider,
                    model=answer.model, sources=source_records(answer),
                    grounding={"passed": report.passed, "issues": report.issues, "warnings": report.warnings},
                    timings_ms=answer.timings_ms, latency_ms=answer.timings_ms["total"])
    db.add(row)
    db.commit()
    return row


def record_feedback(db: Session, user_id: uuid.UUID | None, query_id: uuid.UUID, rating: str,
                    comment: str | None) -> ChatFeedback:
    query = db.get(ChatQuery, query_id)
    # Someone else's answer looks exactly like a missing one, so ids cannot be probed.
    if query is None or query.user_id != user_id:
        raise NotFoundError("chat query", str(query_id))
    # One opinion per answer; rating again replaces it. ON CONFLICT is safe even if two
    # requests arrive at the same time (a read-then-insert would race).
    statement = insert(ChatFeedback).values(query_id=query_id, rating=rating, comment=comment)
    statement = statement.on_conflict_do_update(
        index_elements=[ChatFeedback.query_id],
        set_={"rating": statement.excluded.rating, "comment": statement.excluded.comment, "updated_at": func.now()},
    ).returning(ChatFeedback)
    feedback = db.scalars(statement).one()
    db.commit()
    return feedback
