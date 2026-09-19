"""BM25: tokenizer, the ranking properties the formula promises, and the corpus cache."""

import pytest

from app.retrieval.bm25 import Bm25Index, tokenize
from app.retrieval.search import Bm25Cache, SearchFilters, bm25_search
from app.services import documents
from app.services.audit import RequestContext
from tests.helpers import add_document


def test_tokenizer_keeps_codes_whole_and_drops_stopwords():
    assert tokenize("What is 2CEIT78PE7?") == ["2ceit78pe7"]
    assert tokenize("COURSE-2CEIT602 / CM-SYN-POL-004") == ["course", "2ceit602", "cm", "syn", "pol", "004"]


def test_exact_rare_term_beats_near_miss_codes():
    index = Bm25Index.build(["pe7", "pe1", "list"], [
        "2CEIT78PE7 NATURAL LANGUAGE PROCESSING", "2CEIT78PE1 DEEP LEARNING", "list of electives"])
    assert [chunk_id for chunk_id, _ in index.search("2CEIT78PE7", 3)] == ["pe7"]  # others don't match at all


def test_rare_terms_weigh_more_than_common_ones():
    index = Bm25Index.build(list("abcd"), ["course alpha", "course beta", "course gamma", "course zeta"])
    assert index.idf("zeta") > index.idf("course")
    assert index.search("course zeta", 1)[0][0] == "d"


def test_long_chunks_do_not_win_just_by_being_long():
    index = Bm25Index.build(["short", "long"], ["attendance policy", "attendance " + "filler " * 60])
    assert index.search("attendance", 2)[0][0] == "short"


def test_search_respects_eligibility_and_rebuilds_when_it_changes(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "hostel curfew rules"}])
    add_document(db_session, indexer, "DOC-B", [{"text": "hostel mess timings", "source_type": "official"}],
                 source_type="official")
    cache = Bm25Cache()
    assert {h.citation.document_id for h in bm25_search(db_session, cache, "hostel", 5)} == {"DOC-A", "DOC-B"}
    assert [h.citation.document_id for h in bm25_search(db_session, cache, "hostel", 5,
                                                          SearchFilters(source_types=["official"]))] == ["DOC-B"]

    actor = type("Actor", (), {"id": None})()
    documents.change_status(db_session, "DOC-B", "deactivate", actor=actor, context=RequestContext())
    before = cache._corpus
    assert [h.citation.document_id for h in bm25_search(db_session, cache, "hostel", 5)] == ["DOC-A"]
    assert cache._corpus is not before  # the fingerprint changed, so the corpus was rebuilt


def test_unchanged_corpus_is_not_rebuilt(db_session, indexer):
    add_document(db_session, indexer, "DOC-A", [{"text": "hostel curfew rules"}])
    cache = Bm25Cache()
    first = cache.get(db_session)
    assert cache.get(db_session) is first


@pytest.mark.parametrize("mode", ["bm25", "vector"])
def test_search_api_modes(db_session, indexer, mode):
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.main import app
    from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
    from tests.helpers import API, headers_for

    add_document(db_session, indexer, "DOC-A", [{"text": "hostel curfew rules"}])
    app.dependency_overrides.update({get_db: lambda: db_session, get_embedder: lambda: indexer.embedder,
                                     get_vector_index: lambda: indexer.index, get_bm25_cache: Bm25Cache})
    try:
        client = TestClient(app)
        body = client.get(f"{API}/search", params={"q": "hostel curfew", "mode": mode},
                          headers=headers_for(client, db_session, "student")).json()
    finally:
        app.dependency_overrides.clear()
    assert body["mode"] == mode and body["hits"][0]["citation"]["document_id"] == "DOC-A"
    assert mode in body["hits"][0]["scores"]
