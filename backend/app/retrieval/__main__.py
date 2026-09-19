"""Retrieval command line.

    python -m app.retrieval rebuild-index [--reset]   re-embed every chunk from PostgreSQL
    python -m app.retrieval search "question" [-k 5] [--mode hybrid|vector|bm25] [--official]
"""

import argparse
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.models.documents import Document, DocumentChunk
from app.retrieval.runtime import get_bm25_cache, get_indexer
from app.retrieval.search import SearchFilters, bm25_search, hybrid_search, vector_search


def rebuild_index(reset: bool) -> int:
    """The vector index is derived data: rebuild it entirely from document_chunks."""
    indexer = get_indexer()
    if reset:
        indexer.index.reset()
    total = 0
    with SessionLocal() as db:
        for document in db.scalars(select(Document).order_by(Document.document_id)):
            chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document.document_id)
                                .order_by(DocumentChunk.version_no, DocumentChunk.chunk_index)).all()
            indexer.index_chunks(document, chunks)
            total += len(chunks)
            print(f"  {document.document_id:28} {len(chunks):4} chunks")
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.retrieval")
    commands = parser.add_subparsers(dest="command", required=True)
    rebuild = commands.add_parser("rebuild-index", help="re-embed all chunks into the vector index")
    rebuild.add_argument("--reset", action="store_true", help="drop the collection first (e.g. after a model change)")
    search = commands.add_parser("search", help="try a query")
    search.add_argument("query")
    search.add_argument("-k", type=int, default=5)
    search.add_argument("--mode", choices=["hybrid", "vector", "bm25"], default="hybrid")
    search.add_argument("--official", action="store_true", help="only official chunks")
    args = parser.parse_args(argv)
    setup_logging(get_settings().log_level)

    if args.command == "rebuild-index":
        print(f"Indexed {rebuild_index(args.reset)} chunks.")
        return 0
    indexer = get_indexer()
    with SessionLocal() as db:
        filters = SearchFilters(source_types=["official"] if args.official else [])
        if args.mode == "bm25":
            hits = bm25_search(db, get_bm25_cache(), args.query, args.k, filters)
        elif args.mode == "vector":
            hits = vector_search(db, indexer.embedder, indexer.index, args.query, args.k, filters)
        else:
            hits = hybrid_search(db, indexer.embedder, indexer.index, get_bm25_cache(), args.query, args.k, filters)
        for hit in hits:
            c = hit.citation
            print(f"{hit.rank}. {hit.score:.3f} [{hit.source_type}] {c.document_id} v{c.version_no} "
                  f"p.{c.page_start} | {c.section or ''}")
            print("   " + hit.text[:160].replace("\n", " / "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
