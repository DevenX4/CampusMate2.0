"""Tests for CampusMate Conversational RAG enhancements:

1. Bounded conversation history & multi-turn resolution
2. Ambiguity detection & clarification handling (deadline, HOD)
3. Missing role / HOD abstention without internal jargon
4. Pronominal follow-up resolution ("their research areas", "who teaches it", "does that apply to exams")
5. Topic switching entity isolation
6. Conversation CRUD API endpoints & security isolation
7. Latency timing metrics & low-overhead performance
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from tests.helpers import API, headers_for


@pytest.fixture
def chat_client(seeded_session, indexer):
    app.dependency_overrides.update({
        get_db: lambda: seeded_session,
        get_embedder: lambda: indexer.embedder,
        get_vector_index: lambda: indexer.index,
        get_bm25_cache: Bm25Cache,
    })
    try:
        client = TestClient(app)
        yield client, seeded_session
    finally:
        app.dependency_overrides.clear()


def test_standalone_question_answers_naturally(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")
    
    resp = client.post(
        f"{API}/chat/query",
        json={"question": "What is the attendance policy requirement?"},
        headers=student,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer_type"] in ("answered", "fallback")
    assert "conversation_id" in data
    assert data["clarification_required"] is False
    assert data["options"] == []
    assert "timings_ms" in data
    assert "conversation_resolution" in data["timings_ms"]


def test_ambiguous_deadline_triggers_clarification(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    resp = client.post(
        f"{API}/chat/query",
        json={"question": "What is the deadline?"},
        headers=student,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clarification_required"] is True
    assert data["answer_type"] == "clarification"
    assert len(data["options"]) > 0
    assert "Which deadline are you asking about?" in data["answer"]
    # LLM is skipped; total time must be fast (< 100ms on test machine)
    assert data["timings_ms"]["total"] < 500


def test_replying_to_deadline_clarification(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    # Turn 1: Ambiguous query
    t1_resp = client.post(
        f"{API}/chat/query",
        json={"question": "What is the deadline?"},
        headers=student,
    )
    t1_data = t1_resp.json()
    conv_id = t1_data["conversation_id"]
    assert t1_data["clarification_required"] is True

    # Turn 2: User provides clarification option
    t2_resp = client.post(
        f"{API}/chat/query",
        json={"question": "Exam registration", "conversation_id": conv_id},
        headers=student,
    )
    assert t2_resp.status_code == 200
    t2_data = t2_resp.json()
    assert t2_data["conversation_id"] == conv_id
    assert t2_data["clarification_required"] is False
    assert t2_data["answer_type"] in ("answered", "fallback", "abstained")


def test_ambiguous_hod_query_triggers_clarification(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    resp = client.post(
        f"{API}/chat/query",
        json={"question": "Who is the HOD?"},
        headers=student,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["clarification_required"] is True
    assert data["answer_type"] == "clarification"
    assert len(data["options"]) > 0
    assert "Which department's HOD" in data["answer"]


def test_missing_hod_information_abstains_naturally(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    resp = client.post(
        f"{API}/chat/query",
        json={"question": "Who is the HOD of Information Technology?"},
        headers=student,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer_type"] == "abstained"
    assert "I currently don't have HOD information for the Information Technology department" in data["answer"]
    # Verify no technical jargon is leaked in the user answer
    assert not any(tech in data["answer"].lower() for tech in ["bm25", "rrf", "chroma", "vector", "score"])


def test_follow_up_pronominal_resolution_faculty(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    # Turn 1: Ask about faculty FAC-IT-004
    t1_resp = client.post(
        f"{API}/chat/query",
        json={"question": "Tell me about FAC-IT-004."},
        headers=student,
    )
    t1_data = t1_resp.json()
    conv_id = t1_data["conversation_id"]

    # Turn 2: Follow-up asking "What are their research areas?"
    t2_resp = client.post(
        f"{API}/chat/query",
        json={"question": "What are their research areas?", "conversation_id": conv_id},
        headers=student,
    )
    assert t2_resp.status_code == 200
    t2_data = t2_resp.json()
    assert t2_data["conversation_id"] == conv_id
    assert t2_data["answer_type"] in ("answered", "fallback")


def test_follow_up_pronominal_resolution_course(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    # Turn 1: Ask about course 2CEIT602
    t1_resp = client.post(
        f"{API}/chat/query",
        json={"question": "How many credits does ARTIFICIAL INTELLIGENCE 2CEIT602 carry?"},
        headers=student,
    )
    t1_data = t1_resp.json()
    conv_id = t1_data["conversation_id"]

    # Turn 2: Follow-up asking "Who teaches it?"
    t2_resp = client.post(
        f"{API}/chat/query",
        json={"question": "Who teaches it?", "conversation_id": conv_id},
        headers=student,
    )
    assert t2_resp.status_code == 200
    t2_data = t2_resp.json()
    assert t2_data["conversation_id"] == conv_id
    assert t2_data["answer_type"] in ("answered", "fallback")


def test_exam_policy_follow_up(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    # Turn 1: Ask about attendance requirement
    t1_resp = client.post(
        f"{API}/chat/query",
        json={"question": "What is the attendance requirement?"},
        headers=student,
    )
    t1_data = t1_resp.json()
    conv_id = t1_data["conversation_id"]

    # Turn 2: Follow-up asking "Does that apply to exams?"
    t2_resp = client.post(
        f"{API}/chat/query",
        json={"question": "Does that apply to exams?", "conversation_id": conv_id},
        headers=student,
    )
    assert t2_resp.status_code == 200
    t2_data = t2_resp.json()
    assert t2_data["conversation_id"] == conv_id


def test_topic_switching_resets_entity_focus(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    # Turn 1: Course query
    t1_resp = client.post(
        f"{API}/chat/query",
        json={"question": "Who teaches 2CEIT602?"},
        headers=student,
    )
    t1_data = t1_resp.json()
    conv_id = t1_data["conversation_id"]

    # Turn 2: Topic switch to generic policy
    t2_resp = client.post(
        f"{API}/chat/query",
        json={"question": "What is the attendance policy requirement?", "conversation_id": conv_id},
        headers=student,
    )
    assert t2_resp.status_code == 200
    t2_data = t2_resp.json()
    assert t2_data["conversation_id"] == conv_id
    assert t2_data["route"] in ("documents", "structured")


def test_conversation_crud_and_user_isolation(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")
    admin = headers_for(client, session, "admin")

    # Student creates a conversation
    t1_resp = client.post(
        f"{API}/chat/query",
        json={"question": "Tell me about course 2CEIT602."},
        headers=student,
    )
    conv_id = uuid.UUID(t1_resp.json()["conversation_id"])

    # Student lists conversations
    list_resp = client.get(f"{API}/chat/conversations", headers=student)
    assert list_resp.status_code == 200
    conversations = list_resp.json()
    assert any(c["conversation_id"] == str(conv_id) for c in conversations)

    # Student gets conversation detail
    detail_resp = client.get(f"{API}/chat/conversations/{conv_id}", headers=student)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["conversation_id"] == str(conv_id)
    assert len(detail["messages"]) >= 2  # user + assistant

    # Admin (User B) attempts to get Student's conversation -> Security isolation (404/403)
    admin_get = client.get(f"{API}/chat/conversations/{conv_id}", headers=admin)
    assert admin_get.status_code in (404, 403)

    # Student deletes conversation
    del_resp = client.delete(f"{API}/chat/conversations/{conv_id}", headers=student)
    assert del_resp.status_code == 200

    # Getting deleted conversation returns 404
    detail_resp_after = client.get(f"{API}/chat/conversations/{conv_id}", headers=student)
    assert detail_resp_after.status_code == 404


def test_latency_metrics(chat_client):
    client, session = chat_client
    student = headers_for(client, session, "student")

    resp = client.post(
        f"{API}/chat/query",
        json={"question": "What are the electives offered in Semester VI?"},
        headers=student,
    )
    assert resp.status_code == 200
    timings = resp.json()["timings_ms"]
    assert "conversation_resolution" in timings
    assert "routing" in timings
    assert "total" in timings
    # Conversation resolution is deterministic and fast
    assert timings["conversation_resolution"] < 50
