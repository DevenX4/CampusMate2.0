"""CampusMate Real Live End-to-End Proof Test

Executes live questions against the REAL PostgreSQL database, REAL OKF knowledge graph,
REAL Chroma vector index, REAL BM25 lexical index, RRF fusion, Context Builder,
and Grounding Validator.
"""

import time
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.retrieval.embeddings import BgeEmbedder
from app.retrieval.vector_index import VectorIndex
from app.retrieval.search import Bm25Cache, vector_ranking, bm25_ranking, reciprocal_rank_fusion, SearchFilters, load_hits
from app.routing.evidence import RetrievalDeps, gather
from app.routing.entities import EntityResolver
from app.routing.router import decide
from app.chat.context import build_context
from app.chat.pipeline import answer_question
from app.generation.extractive import ExtractiveProvider
from app.generation.runtime import get_generator


def run_live_tests():
    s = get_settings()
    db = SessionLocal()
    embedder = BgeEmbedder(s.embedding_model, s.model_cache_dir)
    vector_index = VectorIndex(s.storage_dir / "chroma", s.chroma_collection, embedder.model_name, embedder.dimension)
    bm25_cache = Bm25Cache()
    deps = RetrievalDeps(embedder=embedder, index=vector_index, bm25=bm25_cache)
    generator = get_generator()

    print("=" * 60)
    print(" CAMPUSMATE LIVE END-TO-END TRACE & VERIFICATION")
    print("=" * 60)
    print(f"Database         : REAL PostgreSQL ({s.db_host}:{s.db_port}/{s.db_name})")
    print(f"Chroma Collection: {s.chroma_collection} ({vector_index.count()} chunks)")
    print(f"BM25 Corpus      : {len(bm25_cache.get(db).index.ids)} chunks")
    print(f"Generation Engine: {generator.name} (Model: {generator.model or 'N/A'})")
    print("=" * 60)

    # Test 3 detailed trace
    q3 = "What is the attendance requirement for exams?"
    print("\n" + "=" * 60)
    print(" DETAILED LIVE TRACE FOR TEST 3 — HYBRID RAG")
    print("=" * 60)
    print(f"QUESTION: {q3}\n")

    t0 = time.perf_counter()
    res3 = EntityResolver(db).resolve(q3)
    dec3 = decide(q3, res3)
    t_route = round((time.perf_counter() - t0) * 1000)

    print("------------------------------------------------------------")
    print("1. ROUTER")
    print("------------------------------------------------------------")
    print(f"route       : {dec3.route}")
    print(f"intents     : {dec3.intents}")
    print(f"entity      : {res3.entity_ids}")
    print(f"reasons     : {dec3.reasons}")

    t1 = time.perf_counter()
    filters3 = SearchFilters(source_types=["official"] if res3.official_only else [])
    v_hits = vector_ranking(db, deps.embedder, deps.index, q3, 10, filters3)
    t_dense = round((time.perf_counter() - t1) * 1000)

    print("\n------------------------------------------------------------")
    print("2. DENSE RETRIEVAL (Chroma + BAAI/bge-small-en-v1.5)")
    print("------------------------------------------------------------")
    print(f"candidate count : {len(v_hits)}")
    for rank, (cid, score) in enumerate(v_hits[:3], 1):
        print(f"#{rank} score={score:.4f} | chunk_id={cid}")

    t2 = time.perf_counter()
    b_hits = bm25_ranking(db, deps.bm25, q3, 10, filters3)
    t_bm25 = round((time.perf_counter() - t2) * 1000)

    print("\n------------------------------------------------------------")
    print("3. BM25 RETRIEVAL (Lexical Keyword Index)")
    print("------------------------------------------------------------")
    print(f"candidate count : {len(b_hits)}")
    for rank, (cid, score) in enumerate(b_hits[:3], 1):
        print(f"#{rank} score={score:.4f} | chunk_id={cid}")

    t3 = time.perf_counter()
    rankings_dict = {
        "vector": [cid for cid, _ in v_hits],
        "bm25": [cid for cid, _ in b_hits],
    }
    fused = reciprocal_rank_fusion(rankings_dict)
    evidence3 = gather(db, q3, dec3, deps)
    t_retrieval = round((time.perf_counter() - t3) * 1000) + t_dense + t_bm25

    print("\n------------------------------------------------------------")
    print("4. RRF FUSION (Reciprocal Rank Fusion)")
    print("------------------------------------------------------------")
    for rank, (cid, score, method_ranks) in enumerate(fused[:3], 1):
        print(f"#{rank} rrf_score={score:.4f} | chunk_id={cid} | ranks={method_ranks}")

    t4 = time.perf_counter()
    ctx3 = build_context(evidence3, res3.official_only)
    t_ctx = round((time.perf_counter() - t4) * 1000)
    ctx_chars = sum(len(b.text) for b in ctx3.blocks)

    print("\n------------------------------------------------------------")
    print("5. CONTEXT BUILDER")
    print("------------------------------------------------------------")
    print(f"blocks      : {len(ctx3.blocks)} / 8")
    print(f"characters  : {ctx_chars} / 6000")
    for idx, b in enumerate(ctx3.blocks[:3], 1):
        preview = b.text.replace('\n', ' ')[:90]
        print(f"[{idx}] ref=[{b.ref}] source_type={b.source_type} | label={b.label} | text: \"{preview}...\"")

    print("\n------------------------------------------------------------")
    print("6. GENERATION ENGINE & GROUNDING")
    print("------------------------------------------------------------")
    ans3 = answer_question(db, q3, deps, generator)
    print(f"provider        : {ans3.provider}")
    print(f"model           : {ans3.model}")
    print(f"answer_type     : {ans3.answer_type}")
    print(f"grounding status: {'PASS' if ans3.grounding.passed else 'FAIL'}")
    print(f"grounding report: cited={ans3.grounding.cited}, issues={ans3.grounding.issues}, warnings={ans3.grounding.warnings}")

    print("\n------------------------------------------------------------")
    print("7. FINAL ANSWER")
    print("------------------------------------------------------------")
    print(f"{ans3.answer}")

    print("\n------------------------------------------------------------")
    print("8. TIMINGS")
    print("------------------------------------------------------------")
    print(f"routing       : {ans3.timings_ms.get('routing', t_route)} ms")
    print(f"retrieval     : {ans3.timings_ms.get('retrieval', t_retrieval)} ms")
    print(f"context       : {ans3.timings_ms.get('context', t_ctx)} ms")
    print(f"generation    : {ans3.timings_ms.get('generation', 0)} ms")
    print(f"grounding     : {ans3.timings_ms.get('grounding', 0)} ms")
    print(f"TOTAL         : {ans3.timings_ms.get('total', 0)} ms")
    print("=" * 60)

    # Run remaining live questions
    questions = [
        ("TEST 1 — STRUCTURED", "What is 2CEIT602 and how many credits does it have?"),
        ("TEST 2 — GRAPH", "Which faculty member teaches 2CEIT602?"),
        ("TEST 3 — HYBRID RAG", "What is the attendance requirement for exams?"),
        ("TEST 4 — SYNTHETIC PROVENANCE", "Who teaches ARTIFICIAL INTELLIGENCE?"),
        ("TEST 5 — HALLUCINATION", "Is LAB-IT-011 open on Sundays?"),
        ("TEST 6 — UNKNOWN QUESTION", "What is the hostel curfew time for 3rd semester?"),
    ]

    print("\n" + "=" * 60)
    print(" ALL 6 LIVE QUESTIONS RESULTS MATRIX")
    print("=" * 60)
    for title, q in questions:
        ans = answer_question(db, q, deps, generator)
        print(f"\n[{title}]")
        print(f"Q: '{q}'")
        print(f"  -> Route: {ans.route} | Type: {ans.answer_type} | Time: {ans.timings_ms.get('total', 0)}ms")
        print(f"  -> Answer: {ans.answer[:120]}...")

    db.close()

if __name__ == "__main__":
    run_live_tests()
