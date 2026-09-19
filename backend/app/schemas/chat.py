import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import SourceType
from app.schemas.search import Citation

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=500)]


class ChatRequest(BaseModel):
    question: Question


class SourceOut(BaseModel):
    ref: int = Field(description="The number the answer cites as [ref]")
    kind: Literal["structured", "graph", "document"]
    source_type: SourceType
    cited: bool = Field(description="Whether the answer cites this source")
    label: str
    text: str = Field(description="Exactly what the answer was written from")
    citation: Citation


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
    sources: list[SourceOut]
    grounding: GroundingOut
    provider: str
    model: str
    timings_ms: dict[str, int]


class FeedbackRequest(BaseModel):
    query_id: uuid.UUID
    rating: Literal["up", "down"]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class FeedbackResponse(BaseModel):
    query_id: uuid.UUID
    rating: Literal["up", "down"]
    comment: str | None
