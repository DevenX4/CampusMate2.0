"""Query routing: rules (no database), entity resolution and evidence on the real dataset."""

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from app.routing.entities import EntityResolver, Resolution
from app.routing.evidence import _band_range, course_facts, graph_evidence, grade_for_marks, program_summary, semester_courses
from app.routing.router import decide
from tests.helpers import API, headers_for

# --- rules ------------------------------------------------------------------------------------


@pytest.mark.parametrize("question,resolution,route,first_intent", [
    ("Remind me about the fee deadline", Resolution(), "automation", "automation"),
    ("What are my marks in DBMS?", Resolution(), "personal", "personal_record"),
    ("How many credits does AI carry?", Resolution(["COURSE-X"]), "structured", "course_facts"),
    ("What courses are offered in sem 6?", Resolution(semester_ids=["SEM-BTECH-IT-06"]), "structured", "semester_courses"),
    ("Total credits of B.Tech IT?", Resolution(program_ids=["PROG-BTECH-IT-001"]), "structured", "program_summary"),
    ("What grade do I get for 85 marks?", Resolution(numbers=[85.0]), "structured", "grade_for_marks"),
    ("Who teaches COURSE-X?", Resolution(["COURSE-X"]), "graph", "entity_relations"),
    ("What is FAC-IT-004?", Resolution(["FAC-IT-004"]), "graph", "entity_lookup"),
    ("Explain the attendance rules", Resolution(), "documents", "documents"),
])
def test_routing_rules(question, resolution, route, first_intent):
    decision = decide(question, resolution)
    assert (decision.route, decision.intents[0]) == (route, first_intent)
    assert decision.reasons  # every decision explains itself


def test_non_personal_routes_are_always_supported_by_documents():
    decision = decide("How many credits does AI carry and who teaches it?", Resolution(["COURSE-X"]))
    assert decision.intents == ["course_facts", "entity_relations", "documents"]


def test_grade_ranges_as_printed_in_the_syllabus():
    assert _band_range("90>=") == (90.0, 100.0)
    assert _band_range("80 To 89") == (80.0, 89.99)
    assert _band_range("<40")[1] < 40


# --- with the real dataset --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def resolver(seeded_session):
    return EntityResolver(seeded_session)


@pytest.mark.parametrize("question,expected", [
    ("How many credits does ARTIFICIAL INTELLIGENCE carry?", ["COURSE-2CEIT602"]),
    ("Which faculty member teaches the AI course?", ["COURSE-2CEIT602"]),  # acronym
    ("What is 2CEIT78PE7?", ["COURSE-2CEIT78PE7"]),                          # printed code
    ("What does policy CM-SYN-POL-004 cover?", ["POLICY-004"]),              # policy number
    ("What is the specialization of FAC-IT-004?", ["FAC-IT-004"]),          # ID
])
def test_entity_resolution(resolver, question, expected):
    assert resolver.resolve(question).entity_ids == expected


def test_it_in_btech_it_is_not_a_course_acronym(resolver):
    resolution = resolver.resolve("What courses are offered in Semester VI of B.Tech IT?")
    assert resolution.entity_ids == []  # "IT" is also the acronym of several course names
    assert (resolution.program_ids, resolution.semester_ids) == (["PROG-BTECH-IT-001"], ["SEM-BTECH-IT-06"])


def test_semester_without_programme(resolver):
    assert resolver.resolve("courses in sem 7").semester_ids == ["SEM-BTECH-IT-07"]  # M.Tech has only 4
    assert resolver.resolve("courses in 2nd semester").semester_ids == ["SEM-BTECH-IT-02", "SEM-MTECH-IT-02"]


def test_structured_evidence_is_exact_and_cited(seeded_session):
    [fact] = course_facts(seeded_session, ["COURSE-2CEIT602"])
    assert "4 credits (theory 3 + practical/TW 1)" in fact.text and "150 total marks" in fact.text
    assert (fact.source_type, fact.citation.document_id, fact.citation.page_start) == (
        "official", "DOC-OFFICIAL-SYLLABUS-001", 15)
    [summary] = program_summary(seeded_session, ["PROG-BTECH-IT-001"])
    assert "8 semesters and 174 credits" in summary.text and summary.source_type == "derived_official"
    [semester] = semester_courses(seeded_session, ["SEM-BTECH-IT-06"], "courses in semester VI")
    assert "2CEIT602 ARTIFICIAL INTELLIGENCE" in semester.text and "ELECTIVE-III" in semester.text
    [grade] = grade_for_marks(seeded_session, [85.0])
    assert "grade A (grade point 9)" in grade.text


def test_graph_evidence_follows_multi_hop_relations(seeded_session):
    evidence = graph_evidence(seeded_session, ["COURSE-2CEIT78PE7"])
    ids = [e.entity_ids[0] for e in evidence]
    assert ids[0] == "COURSE-2CEIT78PE7"
    assert {"LAB-IT-002", "FAC-IT-003"} <= set(ids)  # practicals lab and its manager
    assert not any(i.startswith(("PROG-", "SEM-", "EGRP-")) for i in ids)  # hubs are not expanded
    lab = next(e for e in evidence if e.entity_ids[0] == "LAB-IT-002")
    assert lab.source_type == "synthetic"


def test_route_api(seeded_session, indexer):
    app.dependency_overrides.update({get_db: lambda: seeded_session, get_embedder: lambda: indexer.embedder,
                                     get_vector_index: lambda: indexer.index, get_bm25_cache: Bm25Cache})
    try:
        client = TestClient(app)
        student = headers_for(client, seeded_session, "student")
        body = client.get(f"{API}/route", params={"q": "How many credits does ARTIFICIAL INTELLIGENCE carry?"},
                          headers=student).json()
        personal = client.get(f"{API}/route", params={"q": "What are my marks?"}, headers=student).json()
    finally:
        app.dependency_overrides.clear()
    assert body["route"] == "structured" and body["evidence"][0]["kind"] == "structured"
    assert body["evidence"][0]["citation"]["page_start"] == 15
    assert personal["route"] == "personal" and personal["evidence"] == []
