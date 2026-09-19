import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import AUTH_ERRORS, DbSession, require
from app.retrieval.embeddings import Embedder
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from app.retrieval.vector_index import VectorIndex
from app.routing.entities import EntityResolver
from app.routing.evidence import RetrievalDeps, gather
from app.routing.router import decide
from app.schemas.routing import EvidenceOut, ResolvedEntities, RouteResponse

router = APIRouter(prefix="/route", tags=["search"], responses=AUTH_ERRORS,
                   dependencies=[Depends(require("chat:use"))])


@router.get("", response_model=RouteResponse)
def route_question(
    db: DbSession,
    embedder: Annotated[Embedder, Depends(get_embedder)],
    index: Annotated[VectorIndex, Depends(get_vector_index)],
    bm25: Annotated[Bm25Cache, Depends(get_bm25_cache)],
    q: Annotated[str, Query(min_length=2, max_length=500)],
):
    """How CampusMate would answer a question: the route (structured / graph / documents /
    personal / automation), the reasons, and the evidence it would use, each with citation."""
    started = time.perf_counter()
    resolution = EntityResolver(db).resolve(q)
    decision = decide(q, resolution)
    evidence = [] if decision.route in ("personal", "automation") else gather(
        db, q, decision, RetrievalDeps(embedder, index, bm25))
    return RouteResponse(
        question=q, route=decision.route, intents=decision.intents, reasons=decision.reasons,
        resolved=ResolvedEntities(entity_ids=resolution.entity_ids, program_ids=resolution.program_ids,
                                  semester_ids=resolution.semester_ids, official_only=resolution.official_only),
        evidence=[EvidenceOut(kind=e.kind, text=e.text, source_type=e.source_type, citation=e.citation,
                              entity_ids=e.entity_ids) for e in evidence],
        took_ms=round((time.perf_counter() - started) * 1000))
