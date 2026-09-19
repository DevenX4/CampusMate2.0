"""Chat: context building, grounding validation, the pipeline with fake generators, and the API."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.chat.context import MAX_GRAPH_BLOCKS, build_context, label
from app.chat.grounding import validate
from app.chat.pipeline import UNSUPPORTED, answer_question
from app.core.db import get_db
from app.generation.base import ABSTAIN_MESSAGE, ContextBlock, GenerationError, GenerationResult
from app.generation.extractive import ExtractiveProvider, extract_answer
from app.generation.runtime import get_generator
from app.main import app
from app.models.chat import ChatFeedback, ChatQuery
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from app.routing.evidence import Evidence, RetrievalDeps
from app.schemas.search import Citation
from tests.helpers import API, headers_for

AI_QUESTION = "How many credits does ARTIFICIAL INTELLIGENCE carry?"


def evidence(kind: str, text: str, source_type: str = "official", page: int = 1) -> Evidence:
    citation = Citation(document_id="DOC-X", version_no=1, title="Doc X", document_type="pdf",
                        page_start=page, page_end=page, section=None)
    return Evidence(kind, text, source_type, citation)


BLOCKS = [
    ContextBlock(1, "structured", "official", "DOC-SYL, p.15", "2CEIT602 ARTIFICIAL INTELLIGENCE: 4 credits, 150 total marks."),
    ContextBlock(2, "document", "synthetic", "DOC-FAC, p.3", "Dr. Rao teaches ARTIFICIAL INTELLIGENCE."),
    ContextBlock(3, "document", "official", "DOC-CAL, p.2", "Examinations start on 12 May."),
]


# --- context builder ------------------------------------------------------------------------

def test_context_keeps_order_numbers_sources_and_removes_duplicates():
    items = [evidence("structured", "fact A"), evidence("graph", "item B"), evidence("document", "fact A"),
             evidence("document", "passage C", page=7)]
    context = build_context(items)
    assert [(b.ref, b.kind, b.text) for b in context.blocks] == [
        (1, "structured", "fact A"), (2, "graph", "item B"), (3, "document", "passage C")]
    assert context.evidence[3] is items[3] and context.blocks[2].label == "DOC-X, p.7 (Doc X)"


def test_context_budget_graph_cap_and_official_filter():
    graph = [evidence("graph", f"graph item {i}") for i in range(6)]
    assert sum(b.kind == "graph" for b in build_context(graph).blocks) == MAX_GRAPH_BLOCKS
    long = [evidence("document", ("word " * 280) + str(i)) for i in range(10)]  # ~1,400 characters each
    assert sum(len(b.text) for b in build_context(long).blocks) <= 6000
    mixed = [evidence("document", "official text"), evidence("document", "demo text", "synthetic")]
    assert [b.text for b in build_context(mixed, official_only=True).blocks] == ["official text"]


def test_label_shows_page_ranges():
    e = evidence("document", "x")
    e.citation.page_end = 4
    assert label(e) == "DOC-X, pp.1-4 (Doc X)"


# --- grounding --------------------------------------------------------------------------------

def test_grounded_answer_passes():
    report = validate("ARTIFICIAL INTELLIGENCE (2CEIT602) carries 4 credits and 150 marks [1].", BLOCKS)
    assert (report.passed, report.cited, report.issues) == (True, [1], [])


def test_letters_inside_codes_are_not_names():
    # Found by the answer evaluation: "CEIT" in "2CEIT602" was reported as an unknown name.
    report = validate("The course is ARTIFICIAL INTELLIGENCE, code 2CEIT602 [1].", BLOCKS)
    assert report.passed, report.issues
    assert "'2ceit999' occurs in no source" in validate("The code is 2CEIT999 [1].", BLOCKS).issues


@pytest.mark.parametrize("answer,issue", [
    ("ARTIFICIAL INTELLIGENCE carries 6 credits [1].", "'6' occurs in no source"),
    ("It is taught by Dr. Mehta [2].", "names that occur in no source: Mehta"),
    ("It carries 4 credits [9].", "cites sources that do not exist: [9]"),
    ("It carries 4 credits.", "the answer cites no source"),
])
def test_ungrounded_answers_fail(answer, issue):
    report = validate(answer, BLOCKS)
    assert not report.passed and issue in report.issues


@pytest.mark.parametrize("answer", [ABSTAIN_MESSAGE, "Sorry, the sources do not mention the hostel curfew.", ""])
def test_refusals_become_the_canonical_abstention(answer):
    report = validate(answer, BLOCKS)
    assert (report.abstained, report.passed, report.answer) == (True, True, ABSTAIN_MESSAGE)


def test_uncited_fact_is_a_warning_and_undisclosed_synthetic_source_gets_a_notice():
    report = validate("Dr. Rao teaches ARTIFICIAL INTELLIGENCE, which has 150 marks [2].", BLOCKS)
    assert report.passed
    assert "'150' occurs only in a source the answer does not cite" in report.warnings
    assert report.answer.endswith("Note: [2] contains synthetic demo data, not official GUNI information.")


@pytest.mark.parametrize("question", [AI_QUESTION, "Who teaches ARTIFICIAL INTELLIGENCE?", "When do examinations start?"])
def test_extractive_answers_always_pass_grounding(question):
    report = validate(extract_answer(question, BLOCKS), BLOCKS)
    assert report.passed and report.warnings == []  # the demo-data disclaimer is not an uncited claim


# --- pipeline -----------------------------------------------------------------------------------

class FakeGenerator:
    name, model = "fake", "fake-1"

    def __init__(self, reply=None, error=False):
        self.reply, self.error, self.calls = reply, error, 0

    def check(self) -> str:
        return "fake"

    def generate(self, request):
        self.calls += 1
        if self.error:
            raise GenerationError("server down")
        text = self.reply(request) if callable(self.reply) else self.reply
        return GenerationResult(text, self.name, self.model, 1)


@pytest.fixture
def deps(indexer):
    return RetrievalDeps(indexer.embedder, indexer.index, Bm25Cache())


def test_grounded_generated_answer_is_used(seeded_session, deps):
    generator = FakeGenerator(lambda request: f"{request.context[0].text} [1]")
    answer = answer_question(seeded_session, AI_QUESTION, deps, generator)
    assert (answer.answer_type, answer.route, answer.provider) == ("answered", "structured", "fake")
    assert "4 credits" in answer.answer and answer.grounding.cited == [1]
    assert set(answer.timings_ms) == {"routing", "evidence", "generation", "grounding", "total"}


@pytest.mark.parametrize("generator,warning", [
    (FakeGenerator("It carries 4 credits and is taught by Dr. Zyxwv Qwerty [1]."), "generated answer rejected: names"),
    (FakeGenerator(error=True), "generation failed"),
])
def test_rejected_or_failed_generation_falls_back_to_extractive(seeded_session, deps, generator, warning):
    answer = answer_question(seeded_session, AI_QUESTION, deps, generator)
    assert answer.answer_type == "fallback" and answer.grounding.passed
    assert "Zyxwv" not in answer.answer and "4 credits" in answer.answer
    assert answer.grounding.warnings[0].startswith(warning)


def test_model_refusal_is_an_abstention(seeded_session, deps):
    answer = answer_question(seeded_session, AI_QUESTION, deps, FakeGenerator("I could not find that in the sources."))
    assert (answer.answer_type, answer.answer) == ("abstained", ABSTAIN_MESSAGE)


def test_personal_questions_are_unsupported_without_generation(seeded_session, deps):
    generator = FakeGenerator("should not be called")
    answer = answer_question(seeded_session, "What are my marks in DBMS?", deps, generator)
    assert (answer.answer_type, answer.answer, generator.calls) == ("unsupported", UNSUPPORTED["personal"], 0)


def test_official_only_questions_see_no_synthetic_sources(seeded_session, deps):
    answer = answer_question(seeded_session, "According to official sources, which lab hosts the practicals of "
                             "ARTIFICIAL INTELLIGENCE?", deps, ExtractiveProvider())
    assert answer.context.blocks and all(b.source_type != "synthetic" for b in answer.context.blocks)


# --- API ----------------------------------------------------------------------------------------

@pytest.fixture
def client(seeded_session, indexer):
    app.dependency_overrides.update({get_db: lambda: seeded_session, get_embedder: lambda: indexer.embedder,
                                     get_vector_index: lambda: indexer.index, get_bm25_cache: Bm25Cache,
                                     get_generator: ExtractiveProvider})
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def ask_api(client, headers, question=AI_QUESTION):
    return client.post(f"{API}/chat/query", json={"question": question}, headers=headers)


def test_chat_query_answers_cites_and_is_logged(client, seeded_session):
    student = headers_for(client, seeded_session, "student")
    response = ask_api(client, student)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer_type"] == "answered" and "4 credits" in body["answer"]
    cited = [s for s in body["sources"] if s["cited"]]
    assert cited[0]["ref"] == 1 and cited[0]["citation"]["page_start"] == 15 and cited[0]["source_type"] == "official"
    row = seeded_session.get(ChatQuery, uuid.UUID(body["query_id"]))
    assert (row.question, row.answer, row.provider, row.grounding["passed"]) == (AI_QUESTION, body["answer"], "extractive", True)
    assert row.sources[0]["cited"] is True and row.latency_ms == body["timings_ms"]["total"]


def test_chat_requires_login_and_a_valid_question(client, seeded_session):
    assert ask_api(client, {}).status_code == 401  # guests do not have chat:use
    student = headers_for(client, seeded_session, "student")
    assert ask_api(client, student, " ? ").status_code == 422  # too short once whitespace is stripped
    assert ask_api(client, student, "x" * 501).status_code == 422


def test_feedback_on_own_answers_only_and_replaced_on_resend(client, seeded_session):
    alice, bob = headers_for(client, seeded_session, "student"), headers_for(client, seeded_session, "faculty")
    query_id = ask_api(client, alice).json()["query_id"]

    def rate(headers, rating, comment=None, qid=query_id):
        return client.post(f"{API}/chat/feedback", json={"query_id": qid, "rating": rating, "comment": comment},
                           headers=headers)

    assert rate(alice, "up").json() == {"query_id": query_id, "rating": "up", "comment": None}
    assert rate(alice, "down", "  Wrong semester  ").json()["comment"] == "Wrong semester"
    count = select(func.count()).select_from(ChatFeedback).where(ChatFeedback.query_id == uuid.UUID(query_id))
    assert seeded_session.scalar(count) == 1  # replaced, not added
    assert rate(bob, "up").status_code == 404  # someone else's answer looks like a missing one
    assert rate(alice, "up", qid=str(uuid.uuid4())).status_code == 404
    assert rate(alice, "meh").status_code == 422
