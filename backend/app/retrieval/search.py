"""Search over document chunks.

Step 1  PostgreSQL: which versions may answer? (active versions of active documents, plus
        any document-level filters)
Step 2  Chroma: the nearest vectors among those versions, with chunk-level filters
Step 3  PostgreSQL: load the chunks by ID, re-checking eligibility, in similarity order

So a deactivated or deleted document disappears from results immediately, with no change
to the vector index, and a stale vector can never produce an answer.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentChunk, DocumentVersion
from app.retrieval.embeddings import Embedder
from app.retrieval.vector_index import VectorIndex, version_key
from app.schemas.search import Citation, SearchHit


@dataclass
class SearchFilters:
    source_types: list[str] = field(default_factory=list)  # e.g. ["official"]
    document_types: list[str] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)
    program_id: str | None = None
    semester_id: str | None = None


def eligible_versions(db: Session, filters: SearchFilters) -> list[tuple[str, int]]:
    query = (select(DocumentVersion.document_id, DocumentVersion.version_no).join(Document)
             .where(DocumentVersion.status == "active", Document.status == "active"))
    if filters.document_types:
        query = query.where(Document.document_type.in_(filters.document_types))
    if filters.document_ids:
        query = query.where(Document.document_id.in_(filters.document_ids))
    return [tuple(row) for row in db.execute(query)]


def chroma_where(versions: list[tuple[str, int]], filters: SearchFilters) -> dict:
    conditions: list[dict] = [{"version_key": {"$in": [version_key(d, v) for d, v in versions]}}]
    if filters.source_types:
        conditions.append({"source_type": {"$in": filters.source_types}})
    if filters.program_id:
        conditions.append({"program_ids": {"$contains": filters.program_id}})
    if filters.semester_id:
        conditions.append({"semester_ids": {"$contains": filters.semester_id}})
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def load_hits(db: Session, ranked: list[tuple[str, float]], score_name: str) -> list[SearchHit]:
    """Chunks for (chunk_id, score) pairs, in the given order, skipping anything that is no
    longer eligible (e.g. a vector left over from a replaced version)."""
    if not ranked:
        return []
    rows = db.execute(
        select(DocumentChunk, Document)
        .join(Document, Document.document_id == DocumentChunk.document_id)
        .join(DocumentVersion, (DocumentVersion.document_id == DocumentChunk.document_id)
              & (DocumentVersion.version_no == DocumentChunk.version_no))
        .where(DocumentChunk.chunk_id.in_([chunk_id for chunk_id, _ in ranked]),
               DocumentVersion.status == "active", Document.status == "active")
    ).all()
    by_id = {str(chunk.chunk_id): (chunk, document) for chunk, document in rows}
    hits = []
    for chunk_id, score in ranked:
        if chunk_id not in by_id:
            continue
        chunk, document = by_id[chunk_id]
        hits.append(SearchHit(
            chunk_id=chunk.chunk_id, rank=len(hits) + 1, score=round(score, 4), text=chunk.text,
            source_type=chunk.source_type, entity_ids=chunk.entity_ids, scores={score_name: round(score, 4)},
            citation=Citation(document_id=chunk.document_id, version_no=chunk.version_no, title=document.title,
                              document_type=document.document_type, page_start=chunk.page_start,
                              page_end=chunk.page_end, section=chunk.section),
        ))
    return hits


def vector_search(db: Session, embedder: Embedder, index: VectorIndex, query: str, k: int,
                  filters: SearchFilters | None = None) -> list[SearchHit]:
    filters = filters or SearchFilters()
    versions = eligible_versions(db, filters)
    if not versions:
        return []
    ranked = index.query(embedder.embed_query(query), k, chroma_where(versions, filters))
    return load_hits(db, ranked, "vector")
