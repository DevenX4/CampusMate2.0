"""Chat history: every question answered, with its sources and grounding result, and the
user's feedback on it. Kept so answers can be audited, feedback can be tied to the exact
evidence that produced an answer, and real questions can become evaluation data."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Identity, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text

from app.models.base import Base, in_list

ANSWER_TYPES = ("answered", "fallback", "abstained", "unsupported")
RATINGS = ("up", "down")


class ChatQuery(Base):
    __tablename__ = "chat_queries"
    __table_args__ = (
        CheckConstraint(in_list("answer_type", ANSWER_TYPES), name="answer_type"),
        CheckConstraint("latency_ms >= 0", name="latency_non_negative"),
        Index("ix_chat_queries_user_id_created_at", "user_id", "created_at"),
    )

    # Random, so a query id cannot be guessed to rate someone else's answer.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # NULL: a guest
    question: Mapped[str]
    route: Mapped[str]
    intents: Mapped[list[str]] = mapped_column(ARRAY(Text))
    answer: Mapped[str]
    answer_type: Mapped[str]
    provider: Mapped[str]
    model: Mapped[str]
    sources: Mapped[list] = mapped_column(JSONB)  # [{ref, document_id, page, cited, ...}]
    grounding: Mapped[dict]  # {passed, issues, warnings}
    timings_ms: Mapped[dict]
    latency_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"
    __table_args__ = (
        CheckConstraint(in_list("rating", RATINGS), name="rating"),
        CheckConstraint("char_length(comment) <= 1000", name="comment_length"),
        UniqueConstraint("query_id"),  # one opinion per answer; giving it again replaces it
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    query_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_queries.id", ondelete="CASCADE"))
    rating: Mapped[str]
    comment: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
