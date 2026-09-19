"""Chat history and feedback."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.chat.pipeline import ChatAnswer
from app.models.chat import ChatFeedback, ChatQuery
from app.services.errors import NotFoundError, RateLimited
from app.services.helpers import contains


def source_records(answer: ChatAnswer) -> list[dict]:
    """What each [ref] pointed at, and whether the answer cited it."""
    cited = set(answer.grounding.cited)
    return [{"ref": ref, "kind": e.kind, "source_type": e.source_type, "document_id": e.citation.document_id,
             "version_no": e.citation.version_no, "page_start": e.citation.page_start,
             "page_end": e.citation.page_end, "entity_ids": e.entity_ids[:10], "cited": ref in cited}
            for ref, e in answer.context.evidence.items()]


def check_rate(db: Session, user_id: uuid.UUID | None, per_minute: int) -> None:
    """At most `per_minute` questions per user in any 60 seconds, counted from the chat log.
    Generating an answer can take seconds of a local model's time; one user must not starve others."""
    if user_id is None:
        return
    since = datetime.now(UTC) - timedelta(seconds=60)
    count, oldest = db.execute(select(func.count(), func.min(ChatQuery.created_at))
                               .where(ChatQuery.user_id == user_id, ChatQuery.created_at >= since)).one()
    if count >= per_minute:
        wait = oldest + timedelta(seconds=60) - datetime.now(UTC)
        raise RateLimited(f"You can ask {per_minute} questions per minute. Please wait a moment.",
                          int(wait.total_seconds()) + 1)


def history(db: Session, user_id: uuid.UUID, q: str | None, limit: int) -> list[ChatQuery]:
    """The user's own questions, newest first."""
    query = select(ChatQuery).where(ChatQuery.user_id == user_id).order_by(ChatQuery.created_at.desc()).limit(limit)
    if q:
        query = query.where(contains(ChatQuery.question, q))
    return list(db.scalars(query))


def analytics(db: Session) -> dict:
    """Usage of the assistant, for administrators. No user identities: questions only."""
    today = datetime.now(UTC).date()
    days = [today - timedelta(days=n) for n in range(6, -1, -1)]
    per_day = dict(db.execute(select(func.date(ChatQuery.created_at), func.count())
                              .where(ChatQuery.created_at >= datetime.combine(days[0], datetime.min.time(), UTC))
                              .group_by(func.date(ChatQuery.created_at))).all())
    count_by = lambda column: dict(db.execute(select(column, func.count()).group_by(column)).all())  # noqa: E731
    ratings = count_by(ChatFeedback.rating)
    p50, p95 = db.execute(select(func.percentile_cont(0.5).within_group(ChatQuery.latency_ms),
                                 func.percentile_cont(0.95).within_group(ChatQuery.latency_ms))).one()
    unanswered = db.execute(select(ChatQuery.question, ChatQuery.created_at)
                            .where(ChatQuery.answer_type == "abstained")
                            .order_by(ChatQuery.created_at.desc()).limit(10)).all()
    downvoted = db.execute(select(ChatQuery.question, ChatFeedback.updated_at, ChatFeedback.comment)
                           .join(ChatFeedback, ChatFeedback.query_id == ChatQuery.id)
                           .where(ChatFeedback.rating == "down")
                           .order_by(ChatFeedback.updated_at.desc()).limit(10)).all()
    return {
        "total_questions": db.scalar(select(func.count()).select_from(ChatQuery)),
        "last_7_days": [{"day": d, "questions": per_day.get(d, 0)} for d in days],
        "by_answer_type": count_by(ChatQuery.answer_type),
        "by_route": count_by(ChatQuery.route),
        "feedback_up": ratings.get("up", 0),
        "feedback_down": ratings.get("down", 0),
        "latency_p50_ms": round(p50) if p50 is not None else None,
        "latency_p95_ms": round(p95) if p95 is not None else None,
        "unanswered": [{"question": q, "created_at": t} for q, t in unanswered],
        "downvoted": [{"question": q, "created_at": t, "comment": c} for q, t, c in downvoted],
    }


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
