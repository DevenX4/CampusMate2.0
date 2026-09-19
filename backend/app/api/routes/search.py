import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import AUTH_ERRORS, DbSession, require
from app.core.config import get_settings
from app.retrieval.embeddings import Embedder
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache, SearchFilters, bm25_search, hybrid_search, vector_search
from app.retrieval.vector_index import VectorIndex
from app.schemas.search import SearchResponse

router = APIRouter(prefix="/search", tags=["search"], responses=AUTH_ERRORS,
                   dependencies=[Depends(require("chat:use"))])

SourceTypeFilter = Literal["official", "derived_official", "synthetic"]


@router.get("", response_model=SearchResponse)
def search(
    db: DbSession,
    embedder: Annotated[Embedder, Depends(get_embedder)],
    index: Annotated[VectorIndex, Depends(get_vector_index)],
    bm25: Annotated[Bm25Cache, Depends(get_bm25_cache)],
    q: Annotated[str, Query(min_length=2, max_length=500, description="The question or keywords")],
    mode: Annotated[Literal["hybrid", "vector", "bm25"],
                    Query(description="hybrid = both, fused (RRF); vector = meaning; bm25 = exact words")] = "hybrid",
    k: Annotated[int | None, Query(ge=1, le=50)] = None,
    source_type: Annotated[list[SourceTypeFilter] | None, Query(description="Repeatable, e.g. official")] = None,
    document_type: Annotated[list[str] | None, Query()] = None,
    program_id: str | None = None,
    semester_id: str | None = None,
):
    """Find the document passages most relevant to a question. Only active versions of active
    documents are searched; every hit carries its citation and source_type."""
    started = time.perf_counter()
    filters = SearchFilters(source_types=source_type or [], document_types=document_type or [],
                            program_id=program_id, semester_id=semester_id)
    k = k or get_settings().retrieval_top_k
    if mode == "bm25":
        hits = bm25_search(db, bm25, q, k, filters)
    elif mode == "vector":
        hits = vector_search(db, embedder, index, q, k, filters)
    else:
        hits = hybrid_search(db, embedder, index, bm25, q, k, filters)
    return SearchResponse(query=q, mode=mode, took_ms=round((time.perf_counter() - started) * 1000), hits=hits)
