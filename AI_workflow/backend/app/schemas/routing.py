from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SourceType
from app.schemas.search import Citation


class ResolvedEntities(BaseModel):
    entity_ids: list[str]
    program_ids: list[str]
    semester_ids: list[str]
    official_only: bool
    unknown_ids: list[str] = Field(default_factory=list, description="Referenced IDs or course codes that do not exist")


class EvidenceOut(BaseModel):
    kind: Literal["structured", "graph", "document"]
    text: str
    source_type: SourceType
    citation: Citation
    entity_ids: list[str]


class RouteResponse(BaseModel):
    question: str
    route: Literal["structured", "graph", "documents", "personal", "automation"]
    intents: list[str]
    reasons: list[str] = Field(description="Why this route: which entities and which words decided it")
    resolved: ResolvedEntities
    evidence: list[EvidenceOut]
    took_ms: int
