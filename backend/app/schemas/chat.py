import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import SourceType
from app.schemas.search import Citation

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]
EntityId = Annotated[str, StringConstraints(pattern=r"^[A-Z]+(-[A-Z0-9]+)+$", max_length=60)]


class ChatRequest(BaseModel):
    question: Question
    program_id: EntityId | None = Field(default=None, description="Selected programme, used when the question names none")
    semester_id: EntityId | None = Field(default=None, description="Selected semester, used when the question names none")


class TableOut(BaseModel):
    ref: int = Field(description="The source [ref] these rows come from")
    title: str
    columns: list[str]
    rows: list[list[str]]


class SourceOut(BaseModel):
    ref: int = Field(description="The number the answer cites as [ref]")
    kind: Literal["structured", "graph", "document"]
    source_type: SourceType
    cited: bool = Field(description="Whether the answer cites this source")
    label: str
    text: str = Field(description="Exactly what the answer was written from")
    citation: Citation
    entity_ids: list[str] = Field(default_factory=list, description="Knowledge-graph entities this source is about")


class GroundingOut(BaseModel):
    passed: bool
    issues: list[str] = Field(description="Why a generated answer was rejected")
    warnings: list[str]


class ChatResponse(BaseModel):
    query_id: uuid.UUID = Field(description="Use it to send feedback on this answer")
    question: str
    answer: str
    answer_type: Literal["answered", "fallback", "abstained", "unsupported"] = Field(
        description="answered: generated and grounded; fallback: the generated answer was rejected (or failed) and "
                    "the extractive answer is shown; abstained: the knowledge base does not say; unsupported: "
                    "a request CampusMate cannot serve yet")
    contains_synthetic: bool = Field(description="A cited source is synthetic demo data, not official GUNI information")
    route: Literal["structured", "graph", "documents", "personal", "automation"]
    intents: list[str]
    reasons: list[str] = Field(description="Why this route: which entities and words decided it")
    tables: list[TableOut] = Field(description="Structured facts behind the answer, as tables (cited sources only)")
    sources: list[SourceOut]
    grounding: GroundingOut
    provider: str
    model: str
    timings_ms: dict[str, int]


class HistoryItem(BaseModel):
    query_id: uuid.UUID
    question: str
    answer_type: str
    created_at: datetime


class DayCount(BaseModel):
    day: date
    questions: int


class RecentQuestion(BaseModel):
    question: str
    created_at: datetime
    comment: str | None = None


class ChatAnalytics(BaseModel):
    total_questions: int
    last_7_days: list[DayCount]
    by_answer_type: dict[str, int]
    by_route: dict[str, int]
    feedback_up: int
    feedback_down: int
    latency_p50_ms: int | None
    latency_p95_ms: int | None
    unanswered: list[RecentQuestion] = Field(description="Recent questions CampusMate abstained on: gaps in the knowledge base")
    downvoted: list[RecentQuestion] = Field(description="Recent answers rated down, with the user's comment")


class FeedbackRequest(BaseModel):
    query_id: uuid.UUID
    rating: Literal["up", "down"]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class FeedbackResponse(BaseModel):
    query_id: uuid.UUID
    rating: Literal["up", "down"]
    comment: str | None
