"""Vector retrieval mechanics: eligibility from PostgreSQL, filters, stale vectors, API.
The test embedder only measures word overlap, so these tests check behaviour, not quality
(retrieval quality is measured by the evaluation harness)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.db import get_db
from app.main import app
from app.models.documents import DocumentChunk
from app.retrieval.runtime import get_embedder, get_vector_index
from app.retrieval.search import SearchFilters, vector_search
from app.retrieval.vector_index import VectorIndex
from app.services import documents
from app.services.audit import RequestContext
from tests.helpers import API, add_document, headers_for, make_indexer


def search(db, indexer, query, **filters):
    return vector_search(db, indexer.embedder, indexer.index, query, 5, SearchFilters(**filters))


def test_most_relevant_chunk_comes_first_with_its_citation(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "attendance policy minimum seventy five percent"},
                                                {"text": "laboratory booking rules and timings"}])
    hits = search(db_session, indexer, "minimum attendance percent")
    assert hits[0].text.startswith("attendance policy")
    assert (hits[0].citation.document_id, hits[0].citation.version_no, hits[0].rank) == ("DOC-A", 1, 1)
    assert hits[0].scores["vector"] == hits[0].score


def test_deactivated_document_disappears_without_touching_the_index(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "attendance policy"}])
    vectors_before = indexer.index.count()
    admin = type("Actor", (), {"id": None})()
    documents.change_status(db_session, "DOC-A", "deactivate", actor=admin, context=RequestContext())
    assert search(db_session, indexer, "attendance policy") == []
    assert indexer.index.count() == vectors_before  # eligibility came from PostgreSQL


def test_only_the_active_version_is_searched(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "attendance policy"}],
                 versions={1: "superseded", 2: "active"})
    hits = search(db_session, indexer, "attendance policy")
    assert [h.citation.version_no for h in hits] == [2]


def test_source_type_and_semester_filters(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [
        {"text": "credits of artificial intelligence", "source_type": "official", "semester_ids": ["SEM-6"]},
        {"text": "credits of artificial intelligence restated", "source_type": "synthetic", "semester_ids": ["SEM-5"]},
    ])
    assert {h.source_type for h in search(db_session, indexer, "credits", source_types=["official"])} == {"official"}
    assert [h.text for h in search(db_session, indexer, "credits", semester_id="SEM-5")] == [
        "credits of artificial intelligence restated"]


def test_a_vector_whose_chunk_is_gone_is_ignored(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "attendance policy"}, {"text": "attendance rules"}])
    db_session.execute(delete(DocumentChunk).where(DocumentChunk.text == "attendance rules"))
    assert [h.text for h in search(db_session, indexer, "attendance")] == ["attendance policy"]


def test_index_refuses_vectors_from_a_different_model(tmp_path):
    make_indexer(tmp_path / "chroma")
    with pytest.raises(RuntimeError, match="rebuild-index"):
        VectorIndex(tmp_path / "chroma", "test-chunks", "some-other-model", 256)


# --- API ----------------------------------------------------------------------------------------

@pytest.fixture
def client(db_session, indexer):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_embedder] = lambda: indexer.embedder
    app.dependency_overrides[get_vector_index] = lambda: indexer.index
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_search_api_requires_chat_permission_and_returns_citations(client, db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "attendance policy minimum"}])
    assert client.get(f"{API}/search", params={"q": "attendance"}).status_code == 401  # guest
    student = headers_for(client, db_session, "student")
    body = client.get(f"{API}/search", params={"q": "attendance", "k": 3, "mode": "vector"}, headers=student).json()
    assert body["mode"] == "vector" and body["hits"][0]["citation"]["document_id"] == "DOC-A"
    assert body["hits"][0]["source_type"] == "synthetic"
    assert client.get(f"{API}/search", params={"q": "x"}, headers=student).status_code == 422  # too short
