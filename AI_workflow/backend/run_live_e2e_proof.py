"""CampusMate Real Live End-to-End Proof Test — 100% Native Hybrid RAG.

Executes live queries against:
  1. Dense ChromaDB Semantic Vector Index (BAAI/bge-small-en-v1.5 embeddings)
  2. Sparse BM25 Lexical Keyword Index (Exact matching for codes & titles)
  3. Reciprocal Rank Fusion (RRF with k=60)
  4. Contextual Generative Synthesizer & Grounding Engine
  5. Strict University Domain Guardrail (Zero outsider query leakage)

No Docker or PostgreSQL required — runs completely natively.
"""

import sys
import time
from pathlib import Path

# Add backend root to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.retrieval.hybrid_engine import (
    HybridRAGEngine,
    ABSTAIN_OUT_OF_SCOPE_MESSAGE,
    ABSTAIN_UNKNOWN_MESSAGE,
    tokenize
)


def run_live_tests():
    print("=" * 70)
    print(" CAMPUSMATE 2.0 HYBRID RAG LIVE PIPELINE VERIFICATION")
    print("=" * 70)

    t_init = time.perf_counter()
    engine = HybridRAGEngine.get_instance()
    init_ms = round((time.perf_counter() - t_init) * 1000)

    total_chunks = len(engine.chunks)
    chroma_count = engine.chroma_collection.count() if engine.chroma_collection else 0
    bm25_terms = len(engine.postings)

    print(f"Architecture     : Dual-Path Hybrid RAG (Dense + BM25 Sparse + RRF)")
    print(f"Knowledge Corpus : {total_chunks} verified university chunks")
    print(f"Chroma Vector DB : {chroma_count} embedded chunks (BAAI/bge-small-en-v1.5)")
    print(f"BM25 Vocabulary  : {bm25_terms} unique lexical postings")
    print(f"Engine Init Time : {init_ms} ms")
    print("=" * 70)

    # ── DEEP STEP-BY-STEP TRACE FOR ATTENDANCE POLICY QUERY ──────────────
    q_trace = "What is the 75% attendance rule?"
    print("\n" + "=" * 70)
    print(" STEP-BY-STEP PIPELINE TRACE FOR LIVE QUERY")
    print(f" Query: \"{q_trace}\"")
    print("=" * 70)

    # Step 1: Domain Guardrail Verification
    t0 = time.perf_counter()
    is_valid = engine._is_valid_campus_query(q_trace)
    t_guard = round((time.perf_counter() - t0) * 1000, 2)
    print("\n[STEP 1] DOMAIN SCOPE GUARDRAIL")
    print(f"  - Decision   : {'IN-SCOPE CAMPUS QUERY (ALLOWED)' if is_valid else 'OUT-OF-SCOPE'}")
    print(f"  - Latency    : {t_guard} ms")

    # Step 2: Dense Semantic Search (Chroma)
    t1 = time.perf_counter()
    v_hits = engine.vector_search(q_trace, k=5)
    t_dense = round((time.perf_counter() - t1) * 1000, 2)
    print("\n[STEP 2] DENSE SEMANTIC VECTOR SEARCH (ChromaDB + ONNX Embedder)")
    print(f"  - Candidates Retrieved : {len(v_hits)} chunks")
    print(f"  - Vector Latency       : {t_dense} ms")
    for rank, (cid, sim) in enumerate(v_hits[:3], 1):
        chunk = engine.chunk_by_id.get(cid, {})
        title = chunk.get("title", cid)
        print(f"    #{rank} Score: {sim:.4f} | ID: {cid[:24]}... | Title: {title}")

    # Step 3: Sparse Lexical Search (BM25)
    t2 = time.perf_counter()
    b_hits = engine.bm25_search(q_trace, k=5)
    t_sparse = round((time.perf_counter() - t2) * 1000, 2)
    print("\n[STEP 3] SPARSE LEXICAL SEARCH (BM25 Robertson/Spärck Jones)")
    print(f"  - Candidates Retrieved : {len(b_hits)} chunks")
    print(f"  - BM25 Latency         : {t_sparse} ms")
    for rank, (cid, score) in enumerate(b_hits[:3], 1):
        chunk = engine.chunk_by_id.get(cid, {})
        title = chunk.get("title", cid)
        print(f"    #{rank} Score: {score:.3f} | ID: {cid[:24]}... | Title: {title}")

    # Step 4: Reciprocal Rank Fusion (RRF k=60)
    t3 = time.perf_counter()
    fused_hits = engine.hybrid_search(q_trace, k=3)
    t_rrf = round((time.perf_counter() - t3) * 1000, 2)
    print("\n[STEP 4] RECIPROCAL RANK FUSION (RRF Fusion k=60)")
    print(f"  - Fused Candidates : {len(fused_hits)}")
    print(f"  - Fusion Latency   : {t_rrf} ms")
    for rank, h in enumerate(fused_hits, 1):
        d = h.get("details", {})
        print(f"    #{rank} Fused Score: {h['score']:.4f} | BM25 Rank: {d.get('bm25_rank', '-')} | Vector Rank: {d.get('vector_rank', '-')} | Title: {h['title']}")

    # Step 5: Grounded Generative Answer Synthesis
    t4 = time.perf_counter()
    full_result = engine.answer_query(q_trace)
    t_total = full_result["timings_ms"].get("total", round((time.perf_counter() - t4) * 1000))

    print("\n[STEP 5] GROUNDED SYNTHESIS & CITATIONS")
    print(f"  - Provider      : {full_result.get('provider')}")
    print(f"  - Route Taken   : {full_result.get('route')}")
    print(f"  - Answer Type   : {full_result.get('answer_type')}")
    print(f"  - Verified Sources : {len(full_result.get('sources', []))} attached")
    print(f"  - Total Latency : {t_total} ms")
    print("\n--- SYNTHESIZED RESPONSE ---")
    print(full_result["answer"])
    print("----------------------------\n")

    # ── FULL TEST MATRIX: IN-SCOPE, UNKNOWN, AND OUTSIDER QUESTIONS ───────
    test_suite = [
        # 1. Core Academic Inquiries (Must Answer With Grounding)
        ("CAMPUS ACADEMIC", "What courses and subjects are offered in Semester 6 B.Tech IT?", "ANSWER"),
        ("CAMPUS FACULTY", "Who is the HOD of IT?", "ANSWER"),
        ("CAMPUS POLICY", "What is the 75% attendance rule?", "ANSWER"),
        ("CAMPUS CODE", "What is 2CEIT601 and what are its credits?", "ANSWER"),
        ("CAMPUS GREETING", "hello", "GREETING"),

        # 2. Unknown University Queries (Must Politely Abstain)
        ("UNKNOWN DEGREE", "What is the syllabus for aerospace engineering semester 8 at Stanford?", "UNKNOWN"),
        ("UNKNOWN FACULTY", "Who is the HOD of Civil Engineering?", "UNKNOWN"),

        # 3. Strict Outsider Questions (Must Strictly Reject)
        ("OUTSIDER POLITICS", "Who is the PM?", "OUTSIDER"),
        ("OUTSIDER MATH", "What is 2 + 2?", "OUTSIDER"),
        ("OUTSIDER LIFESTYLE", "How to lose weight in 30 days?", "OUTSIDER"),
        ("OUTSIDER CODING", "Write python code to reverse a string", "OUTSIDER"),
        ("OUTSIDER TRIVIA", "Tell me a funny joke", "OUTSIDER"),
    ]

    print("=" * 70)
    print(" FULL TEST MATRIX VERIFICATION (12 LIVE QUERIES)")
    print("=" * 70)

    passed_count = 0
    for category, query, expected_type in test_suite:
        res = engine.answer_query(query)
        ans = res["answer"]
        route = res.get("route", "")

        is_outsider = ans == ABSTAIN_OUT_OF_SCOPE_MESSAGE
        is_unknown = ans == ABSTAIN_UNKNOWN_MESSAGE
        is_greeting = route == "greeting"
        is_answer = not is_outsider and not is_unknown and not is_greeting

        status = "FAIL"
        if expected_type == "OUTSIDER" and is_outsider:
            status = "PASS"
        elif expected_type == "UNKNOWN" and is_unknown:
            status = "PASS"
        elif expected_type == "GREETING" and is_greeting:
            status = "PASS"
        elif expected_type == "ANSWER" and is_answer:
            status = "PASS"

        if status == "PASS":
            passed_count += 1

        print(f"[{status}] [{category}]")
        print(f"  Q: \"{query}\"")
        print(f"  A: {ans.replace('\n', ' ')[:95]}...")
        print(f"  Route: {route} | Latency: {res['timings_ms'].get('total', 0)} ms\n")

    print("=" * 70)
    print(f" RESULTS: {passed_count}/{len(test_suite)} TESTS PASSED ({passed_count/len(test_suite)*100:.1f}%)")
    if passed_count == len(test_suite):
        print(" ALL CHECKS PASSED: HYBRID RAG + DOMAIN GUARDRAILS 100% OPERATIONAL")
    print("=" * 70)


if __name__ == "__main__":
    run_live_tests()
