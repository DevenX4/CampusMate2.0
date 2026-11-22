"""End-to-end scenarios over HTTP, on the real dataset: what a student asks and what an admin
does, through the whole stack (API -> PostgreSQL -> documents -> ingestion -> retrieval ->
knowledge graph -> generation -> grounding). Only the embedding model is replaced (the
deterministic test embedder), and generation is the extractive provider.

The uploaded document states a clearly fictitious fact ("the Zephyr reading room"), so an
answer containing it can only have come from that document.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes.documents import storage_root
from app.core.db import get_db
from app.generation.base import ABSTAIN_MESSAGE
from app.generation.extractive import ExtractiveProvider
from app.generation.runtime import get_generator
from app.ingestion.pipeline import process_next
from app.main import app
from app.models.chat import ChatFeedback
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from tests.helpers import API, headers_for, text_pdf

ROOM_QUESTION = "When does the Zephyr reading room open?"


@pytest.fixture
def stack(seeded_session, indexer, tmp_path):
    bm25 = Bm25Cache()
    app.dependency_overrides.update({
        get_db: lambda: seeded_session, storage_root: lambda: tmp_path, get_embedder: lambda: indexer.embedder,
        get_vector_index: lambda: indexer.index, get_bm25_cache: lambda: bm25, get_generator: ExtractiveProvider,
    })
    client = TestClient(app)

    def run_worker():
        while process_next(seeded_session, tmp_path, max_chars=1200, lease_minutes=30, indexer=indexer):
            pass

    try:
        yield client, run_worker, headers_for(client, seeded_session, "student"), headers_for(client, seeded_session, "admin")
    finally:
        app.dependency_overrides.clear()


def ask(client, headers, question):
    response = client.post(f"{API}/chat/query", json={"question": question}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def cited(body):
    return [(s["citation"]["document_id"], s["citation"]["version_no"]) for s in body["sources"] if s["cited"]]


def handbook(opening_time: str) -> dict:
    lines = [["Library services", f"The Zephyr reading room opens at {opening_time} on weekdays.",
              "Books may be borrowed for fourteen days."]]
    return {"file": ("handbook.pdf", text_pdf(lines), "application/pdf")}


def test_student_questions_use_sql_graph_and_the_right_labels(stack):
    client, _, student, _ = stack
    credits = ask(client, student, "How many credits does ARTIFICIAL INTELLIGENCE carry in B.Tech IT?")
    assert credits["route"] == "structured" and "4 credits" in credits["answer"]
    assert cited(credits) == [("DOC-OFFICIAL-SYLLABUS-001", 1)] and credits["sources"][0]["source_type"] == "official"
    assert credits["sources"][0]["citation"]["page_start"] == 15 and not credits["contains_synthetic"]

    lab = ask(client, student, "Which lab hosts the practicals of ARTIFICIAL INTELLIGENCE?")
    assert lab["route"] == "graph" and "LAB-IT-001" in lab["answer"]
    assert lab["contains_synthetic"] and "Synthetic demo data" in lab["answer"]  # the lab record is demo data

    assert ask(client, student, "What are my marks in DBMS?")["answer_type"] == "unsupported"
    assert ask(client, student, "What is the hostel curfew time?")["answer"] == ABSTAIN_MESSAGE


def test_document_lifecycle_reaches_the_answers(stack, seeded_session):
    client, run_worker, student, admin = stack
    form = {"title": "Library Handbook (Synthetic)", "document_type": "handbook", "source_type": "synthetic"}

    # Only an administrator can add knowledge.
    assert client.post(f"{API}/documents", headers=student, files=handbook("07:15"), data=form).status_code == 403
    created = client.post(f"{API}/documents", headers=admin, files=handbook("07:15"), data=form)
    assert created.status_code == 201, created.text
    document_id = created.json()["document_id"]

    # Stored but not yet ingested: nothing can be answered from it.
    assert ask(client, student, ROOM_QUESTION)["answer"] == ABSTAIN_MESSAGE
    run_worker()
    answer = ask(client, student, ROOM_QUESTION)
    assert "07:15" in answer["answer"] and (document_id, 1) in cited(answer)
    assert answer["contains_synthetic"] and answer["answer_type"] == "answered"

    # Feedback is tied to that exact answer.
    rated = client.post(f"{API}/chat/feedback", headers=student, json={"query_id": answer["query_id"], "rating": "up"})
    assert rated.status_code == 200
    stored = select(ChatFeedback.rating).where(ChatFeedback.query_id == uuid.UUID(answer["query_id"]))
    assert seeded_session.scalar(stored) == "up"

    # Deactivated: gone from the answers at once, without touching the index.
    assert client.post(f"{API}/documents/{document_id}/deactivate", headers=admin).status_code == 200
    assert ask(client, student, ROOM_QUESTION)["answer"] == ABSTAIN_MESSAGE
    assert client.post(f"{API}/documents/{document_id}/activate", headers=admin).status_code == 200

    # A new version replaces the fact once it is ingested ...
    replaced = client.post(f"{API}/documents/{document_id}/versions", headers=admin, files=handbook("08:30"))
    assert replaced.status_code == 201, replaced.text
    assert "07:15" in ask(client, student, ROOM_QUESTION)["answer"]  # v1 answers until v2 is ready
    run_worker()
    answer = ask(client, student, ROOM_QUESTION)
    assert "08:30" in answer["answer"] and "07:15" not in answer["answer"] and (document_id, 2) in cited(answer)

    # ... and rolling back brings the old one back.
    assert client.post(f"{API}/documents/{document_id}/versions/1/activate", headers=admin).status_code == 200
    answer = ask(client, student, ROOM_QUESTION)
    assert "07:15" in answer["answer"] and (document_id, 1) in cited(answer)
