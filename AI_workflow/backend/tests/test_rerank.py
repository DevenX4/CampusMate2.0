"""Reranking mechanics with a stand-in reranker (quality is measured by the evaluation harness)."""

from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.retrieval.rerank import OverlapReranker
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index, reranker_provider
from app.retrieval.search import Bm25Cache, reranked_search
from tests.helpers import API, add_document, headers_for


class RecordingReranker:
    """Scores passages by a fixed preference and records what it was shown."""

    model_name = "recording"

    def __init__(self, favourite: str):
        self.favourite, self.seen = favourite, []

    def score(self, query, passages):
        self.seen = passages
        return [1.0 if self.favourite in p else 0.0 for p in passages]


def test_reranker_decides_the_final_order_and_earlier_scores_are_kept(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [
        {"text": "attendance policy attendance rules attendance"},  # hybrid's favourite
        {"text": "attendance exceptions for medical leave"},
    ])
    reranker = RecordingReranker("medical")
    hits = reranked_search(db_session, indexer.embedder, indexer.index, Bm25Cache(), reranker, "attendance", 2)
    assert hits[0].text.startswith("attendance exceptions")  # promoted by the reranker
    assert hits[0].rank == 1 and hits[0].scores["rerank"] == 1.0
    assert hits[0].scores["hybrid_rank"] == 2  # where hybrid had put it: the change is visible
    assert {"rrf", "vector_rank", "bm25_rank"} <= set(hits[0].scores)


def test_reranker_reads_title_section_and_at_most_max_chars(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "attendance " + "x" * 500}])
    reranker = RecordingReranker("nothing")
    hits = reranked_search(db_session, indexer.embedder, indexer.index, Bm25Cache(), reranker, "attendance", 1,
                           max_chars=100)
    assert reranker.seen[0].startswith("Title of DOC-A") and len(reranker.seen[0]) == 100
    assert len(hits[0].text) > 500  # the full chunk is still returned


def test_reranker_is_loaded_only_for_the_rerank_mode(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "hostel curfew rules"}])
    loads = []

    def load():
        loads.append(1)
        return OverlapReranker()

    app.dependency_overrides.update({get_db: lambda: db_session, get_embedder: lambda: indexer.embedder,
                                     get_vector_index: lambda: indexer.index, get_bm25_cache: Bm25Cache,
                                     reranker_provider: lambda: load})
    try:
        client = TestClient(app)
        student = headers_for(client, db_session, "student")
        assert client.get(f"{API}/search", params={"q": "hostel curfew"}, headers=student).json()["mode"] == "hybrid"
        assert loads == []  # default mode: no model loaded
        body = client.get(f"{API}/search", params={"q": "hostel curfew", "mode": "hybrid_rerank"},
                          headers=student).json()
    finally:
        app.dependency_overrides.clear()
    assert loads == [1] and body["mode"] == "hybrid_rerank" and "rerank" in body["hits"][0]["scores"]
