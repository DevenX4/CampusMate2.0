"""Reciprocal Rank Fusion by hand, hybrid search behaviour, and the evaluation's sign test."""

import pytest

from app.evaluation.metrics import sign_test_p
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.search import Bm25Cache, hybrid_search
from tests.helpers import add_document


def test_rrf_by_hand():
    fused = reciprocal_rank_fusion({"vector": ["a", "b", "c"], "bm25": ["c", "a"]}, k=60)
    scores = {chunk_id: score for chunk_id, score, _ in fused}
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)  # 1st and 2nd
    assert scores["c"] == pytest.approx(1 / 63 + 1 / 61)  # 3rd and 1st
    assert scores["b"] == pytest.approx(1 / 62)            # only one list
    assert [chunk_id for chunk_id, _, _ in fused] == ["a", "c", "b"]
    assert fused[0][2] == {"vector": 1, "bm25": 2}


def test_agreement_beats_a_single_first_place():
    fused = reciprocal_rank_fusion({"vector": ["solo", "x", "both"], "bm25": ["y", "z", "both"]})
    assert fused[0][0] == "both"  # 3rd in both lists outranks 1st in only one


def test_hybrid_finds_what_only_one_method_finds_and_explains_it(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [
        {"text": "2CEIT78PE7 natural language processing elective"},
        {"text": "rules for using the computer laboratories"},
    ])
    hits = hybrid_search(db_session, indexer.embedder, indexer.index, Bm25Cache(), "2CEIT78PE7", 2)
    assert hits[0].text.startswith("2CEIT78PE7")
    assert {"rrf", "vector_rank", "bm25_rank"} <= set(hits[0].scores)  # both methods' ranks shown


def test_sign_test():
    assert sign_test_p(10, 0) == pytest.approx(2 / 1024)  # 10 wins out of 10: very unlikely by chance
    assert sign_test_p(5, 5) == 1.0
    assert sign_test_p(0, 0) == 1.0
    assert 0.07 < sign_test_p(15, 6) < 0.09
