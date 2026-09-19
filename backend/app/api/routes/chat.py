from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import AUTH_ERRORS, NOT_FOUND, DbSession, Limit, SearchText, require
from app.chat.pipeline import ChatAnswer, answer_question
from app.core.config import get_settings
from app.generation.base import GenerationProvider
from app.generation.runtime import get_generator
from app.models.auth import User
from app.retrieval.embeddings import Embedder
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from app.retrieval.vector_index import VectorIndex
from app.routing.evidence import RetrievalDeps
from app.schemas.chat import (
    ChatAnalytics, ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse, GroundingOut, HistoryItem, SourceOut,
    TableOut,
)
from app.schemas.common import ErrorResponse
from app.services import chat as chat_service

router = APIRouter(prefix="/chat", tags=["chat"], responses=AUTH_ERRORS)
Asker = Annotated[User | None, Depends(require("chat:use"))]


def to_response(query_id, answer: ChatAnswer) -> ChatResponse:
    cited = set(answer.grounding.cited)
    tables = [TableOut(ref=ref, title=e.table.title, columns=e.table.columns, rows=e.table.rows)
              for ref, e in answer.context.evidence.items() if e.table is not None and ref in cited]
    sources = [SourceOut(ref=b.ref, kind=b.kind, source_type=b.source_type, cited=b.ref in cited, label=b.label,
                         text=b.text, citation=answer.context.evidence[b.ref].citation,
                         entity_ids=answer.context.evidence[b.ref].entity_ids[:12])
               for b in answer.context.blocks]
    return ChatResponse(
        query_id=query_id, question=answer.question, answer=answer.answer, answer_type=answer.answer_type,
        contains_synthetic=any(s.cited and (s.source_type == "synthetic" or "[synthetic]" in s.text) for s in sources),
        route=answer.route, intents=answer.intents, reasons=answer.reasons, tables=tables, sources=sources,
        grounding=GroundingOut(passed=answer.grounding.passed, issues=answer.grounding.issues,
                               warnings=answer.grounding.warnings),
        provider=answer.provider, model=answer.model, timings_ms=answer.timings_ms)


@router.post("/query", response_model=ChatResponse,
             responses={429: {"model": ErrorResponse, "description": "Too many questions; see Retry-After"}})
def chat_query(
    body: ChatRequest,
    db: DbSession,
    user: Asker,
    embedder: Annotated[Embedder, Depends(get_embedder)],
    index: Annotated[VectorIndex, Depends(get_vector_index)],
    bm25: Annotated[Bm25Cache, Depends(get_bm25_cache)],
    generator: Annotated[GenerationProvider, Depends(get_generator)],
):
    """Answer a question from CampusMate's knowledge only, citing the sources used.

    The answer is checked against its sources before it is returned. If the knowledge base does
    not contain the answer, the reply says so instead of guessing (`answer_type` "abstained")."""
    settings = get_settings()
    chat_service.check_rate(db, user.id if user else None, settings.chat_questions_per_minute)
    answer = answer_question(db, body.question, RetrievalDeps(embedder, index, bm25), generator,
                             settings.generation_max_tokens, settings.generation_temperature,
                             program_id=body.program_id, semester_id=body.semester_id)
    row = chat_service.log_answer(db, user.id if user else None, answer)
    return to_response(row.id, answer)


@router.get("/history", response_model=list[HistoryItem])
def chat_history(db: DbSession, user: Asker, q: SearchText = None, limit: Limit = 30):
    """Your own recent questions (newest first), optionally filtered by text."""
    if user is None:
        return []
    return [HistoryItem(query_id=row.id, question=row.question, answer_type=row.answer_type, created_at=row.created_at)
            for row in chat_service.history(db, user.id, q, limit)]


@router.get("/analytics", response_model=ChatAnalytics, dependencies=[Depends(require("audit:read"))])
def chat_analytics(db: DbSession):
    """How the assistant is used: volume, answer types, routes, feedback, latency, and the
    questions it could not answer (administrators; no user identities)."""
    return chat_service.analytics(db)


@router.post("/feedback", response_model=FeedbackResponse, responses=NOT_FOUND)
def chat_feedback(body: FeedbackRequest, db: DbSession, user: Asker):
    """Rate one of your own answers (up or down), with an optional comment. Rating again replaces it."""
    feedback = chat_service.record_feedback(db, user.id if user else None, body.query_id, body.rating, body.comment)
    return FeedbackResponse(query_id=feedback.query_id, rating=feedback.rating, comment=feedback.comment)
