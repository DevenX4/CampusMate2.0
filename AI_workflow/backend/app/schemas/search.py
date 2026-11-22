import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SourceType


class Citation(BaseModel):
    """Everything needed to cite a chunk: which document, which version, which pages."""

    document_id: str
    version_no: int
    title: str
    document_type: str
    page_start: int | None
    page_end: int | None
    section: str | None


class SearchHit(BaseModel):
    chunk_id: uuid.UUID
    rank: int
    score: float = Field(description="Similarity for this retrieval mode (higher = more relevant)")
    text: str
    source_type: SourceType
    entity_ids: list[str]
    citation: Citation
    scores: dict[str, float] = Field(default_factory=dict, description="Per-stage scores, for transparency")


class SearchResponse(BaseModel):
    query: str
    mode: Literal["vector", "bm25", "hybrid", "hybrid_rerank"]
    took_ms: int
    hits: list[SearchHit]
