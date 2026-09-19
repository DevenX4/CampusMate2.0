"""Search over document chunks.

Step 1  PostgreSQL: which versions may answer? (active versions of active documents, plus
        any document-level filters)
Step 2  Chroma: the nearest vectors among those versions, with chunk-level filters
Step 3  PostgreSQL: load the chunks by ID, re-checking eligibility, in similarity order

So a deactivated or deleted document disappears from results immediately, with no change
to the vector index, and a stale vector can never produce an answer.

BM25 (lexical) search works over the same eligible chunks; see Bm25Cache below.
Hybrid search fuses both ranked lists with Reciprocal Rank Fusion (fusion.py).
"""

import threading
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentChunk, DocumentVersion
from app.retrieval.bm25 import Bm25Index
from app.retrieval.embeddings import Embedder, embedding_text
from app.retrieval.fusion import reciprocal_rank_fusion
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


def load_hits(db: Session, ranked: list[tuple[str, float]], score_name: str,
              details: dict[str, dict[str, float]] | None = None) -> list[SearchHit]:
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
            source_type=chunk.source_type, entity_ids=chunk.entity_ids,
            scores={score_name: round(score, 4), **(details or {}).get(chunk_id, {})},
            citation=Citation(document_id=chunk.document_id, version_no=chunk.version_no, title=document.title,
                              document_type=document.document_type, page_start=chunk.page_start,
                              page_end=chunk.page_end, section=chunk.section),
        ))
    return hits


def vector_ranking(db: Session, embedder: Embedder, index: VectorIndex, query: str, k: int,
                   filters: SearchFilters) -> list[tuple[str, float]]:
    versions = eligible_versions(db, filters)
    if not versions:
        return []
    return index.query(embedder.embed_query(query), k, chroma_where(versions, filters))


def vector_search(db: Session, embedder: Embedder, index: VectorIndex, query: str, k: int,
                  filters: SearchFilters | None = None) -> list[SearchHit]:
    return load_hits(db, vector_ranking(db, embedder, index, query, k, filters or SearchFilters()), "vector")


# --- BM25 ---------------------------------------------------------------------------------------

_FINGERPRINT_SQL = text("""
    SELECT count(c.chunk_id), max(c.created_at),
           md5(coalesce(string_agg(DISTINCT v.document_id || '/' || v.version_no, ','
                                   ORDER BY v.document_id || '/' || v.version_no), ''))  -- ':' would be read as a bind parameter
    FROM document_versions v
    JOIN documents d ON d.document_id = v.document_id
    LEFT JOIN document_chunks c ON c.document_id = v.document_id AND c.version_no = v.version_no
    WHERE v.status = 'active' AND d.status = 'active'
""")


@dataclass
class _ChunkAttrs:
    document_id: str
    document_type: str
    source_type: str
    program_ids: frozenset[str]
    semester_ids: frozenset[str]


@dataclass
class Bm25Corpus:
    fingerprint: tuple
    index: Bm25Index
    attrs: list[_ChunkAttrs]


class Bm25Cache:
    """The BM25 statistics of the eligible chunks, kept in memory. Rebuilt whenever the
    fingerprint changes: which versions are active, how many chunks, the newest chunk. So an
    upload, activation or deactivation is reflected on the very next query, and there is no
    separately stored lexical index that could drift out of sync."""

    def __init__(self):
        self._corpus: Bm25Corpus | None = None
        self._lock = threading.Lock()  # API requests run in parallel threads

    def get(self, db: Session) -> Bm25Corpus:
        fingerprint = tuple(db.execute(_FINGERPRINT_SQL).one())
        with self._lock:
            if self._corpus is None or self._corpus.fingerprint != fingerprint:
                self._corpus = self._build(db, fingerprint)
            return self._corpus

    @staticmethod
    def _build(db: Session, fingerprint: tuple) -> Bm25Corpus:
        rows = db.execute(
            select(DocumentChunk, Document.title, Document.document_type)
            .join(Document, Document.document_id == DocumentChunk.document_id)
            .join(DocumentVersion, (DocumentVersion.document_id == DocumentChunk.document_id)
                  & (DocumentVersion.version_no == DocumentChunk.version_no))
            .where(DocumentVersion.status == "active", Document.status == "active")
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        ).all()
        index = Bm25Index.build([str(c.chunk_id) for c, _, _ in rows],
                               [embedding_text(title, c.section, c.text) for c, title, _ in rows])
        attrs = [_ChunkAttrs(c.document_id, document_type, c.source_type,
                             frozenset(c.metadata_.get("program_ids", [])),
                             frozenset(c.metadata_.get("semester_ids", [])))
                 for c, _, document_type in rows]
        return Bm25Corpus(fingerprint, index, attrs)


def _allowed(attrs: list[_ChunkAttrs], filters: SearchFilters):
    def check(i: int) -> bool:
        a = attrs[i]
        return ((not filters.source_types or a.source_type in filters.source_types)
                and (not filters.document_types or a.document_type in filters.document_types)
                and (not filters.document_ids or a.document_id in filters.document_ids)
                and (not filters.program_id or filters.program_id in a.program_ids)
                and (not filters.semester_id or filters.semester_id in a.semester_ids))
    return check


def bm25_ranking(db: Session, cache: Bm25Cache, query: str, k: int, filters: SearchFilters) -> list[tuple[str, float]]:
    corpus = cache.get(db)
    return corpus.index.search(query, k, _allowed(corpus.attrs, filters))


def bm25_search(db: Session, cache: Bm25Cache, query: str, k: int,
                filters: SearchFilters | None = None) -> list[SearchHit]:
    return load_hits(db, bm25_ranking(db, cache, query, k, filters or SearchFilters()), "bm25")


# --- Hybrid -------------------------------------------------------------------------------------

def hybrid_ranking(db: Session, embedder: Embedder, index: VectorIndex, cache: Bm25Cache, query: str,
                   candidates: int, filters: SearchFilters) -> list[tuple[str, float, dict[str, float]]]:
    """(chunk id, fused score, per-method details) for the union of both candidate lists."""
    vector = vector_ranking(db, embedder, index, query, candidates, filters)
    lexical = bm25_ranking(db, cache, query, candidates, filters)
    raw = {"vector": dict(vector), "bm25": dict(lexical)}
    fused = reciprocal_rank_fusion({"vector": [c for c, _ in vector], "bm25": [c for c, _ in lexical]})
    return [
        (chunk_id, score, {**{f"{m}_rank": r for m, r in ranks.items()},
                           **{m: round(raw[m][chunk_id], 4) for m in ranks}})
        for chunk_id, score, ranks in fused
    ]


def hybrid_search(db: Session, embedder: Embedder, index: VectorIndex, cache: Bm25Cache, query: str, k: int,
                  filters: SearchFilters | None = None, candidates: int = 30) -> list[SearchHit]:
    """Vector and BM25 each propose `candidates` chunks; RRF merges them; the best k are returned.
    Each hit's `scores` shows both methods' ranks, so the fusion is explainable."""
    fused = hybrid_ranking(db, embedder, index, cache, query, max(candidates, k), filters or SearchFilters())[:k]
    return load_hits(db, [(c, s) for c, s, _ in fused], "rrf", {c: d for c, _, d in fused})
