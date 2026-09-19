"""The API the redesigned UI relies on: usernames and demo accounts, answer tables and the
selected context, question history, analytics, policies / notices / calendar, knowledge
sources and system information."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import auth as auth_routes
from app.core.config import get_settings
from app.core.db import get_db
from app.generation.extractive import ExtractiveProvider
from app.generation.runtime import get_generator
from app.main import app
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from app.services import users
from app.services.audit import RequestContext
from tests.helpers import API, headers_for


def login(client, name: str, password: str):
    return client.post(f"{API}/auth/login", json={"username": name, "password": password})


@pytest.fixture
def client(seeded_session, indexer):
    app.dependency_overrides.update({get_db: lambda: seeded_session, get_embedder: lambda: indexer.embedder,
                                     get_vector_index: lambda: indexer.index, get_bm25_cache: Bm25Cache,
                                     get_generator: ExtractiveProvider})
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# --- usernames and demo accounts -------------------------------------------------------------------

def test_demo_accounts_log_in_by_username_and_are_listed_for_the_login_page(client, seeded_session):
    users.ensure_demo_accounts(seeded_session, context=RequestContext())
    users.ensure_demo_accounts(seeded_session, context=RequestContext())  # idempotent: resets, never duplicates
    admin = login(client, "admin", "admin@123")
    assert admin.status_code == 200 and admin.json()["user"]["role"] == "admin"
    assert login(client, "STUDENT", "student@123").json()["user"]["username"] == "student"  # case-insensitive
    assert login(client, "admin@campusmate-demo.example", "admin@123").status_code == 200  # email still works
    assert login(client, "admin", "wrong").status_code == 401
    demo = client.get(f"{API}/auth/demo").json()
    assert demo["enabled"] and {a["username"]: a["password"] for a in demo["accounts"]} == {
        "admin": "admin@123", "student": "student@123"}


def test_demo_accounts_cannot_log_in_in_production(client, seeded_session, monkeypatch):
    users.ensure_demo_accounts(seeded_session, context=RequestContext())
    production = get_settings().model_copy(update={"app_env": "production", "cookie_secure": True})
    monkeypatch.setattr(auth_routes, "get_settings", lambda: production)
    assert login(client, "admin", "admin@123").status_code == 401
    assert client.get(f"{API}/auth/demo").json() == {"enabled": False, "accounts": []}


def test_the_old_email_field_still_logs_in(client, seeded_session):
    headers_for(client, seeded_session, "student")  # creates a user with an email and logs in with "email"


# --- chat: tables, context, history, analytics -----------------------------------------------------

def ask(client, headers, question, **context):
    response = client.post(f"{API}/chat/query", json={"question": question, **context}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_structured_answers_carry_their_table(client, seeded_session):
    student = headers_for(client, seeded_session, "student")
    body = ask(client, student, "What courses are offered in Semester VI of B.Tech IT?")
    [table] = body["tables"]
    assert table["columns"] == ["Course code", "Course title", "Credits", "Classification"]
    assert ["2CEIT602", "ARTIFICIAL INTELLIGENCE", "4"] in [row[:3] for row in table["rows"]]
    assert body["sources"][table["ref"] - 1]["cited"] and body["reasons"]


def test_the_selected_semester_applies_when_the_question_names_none(client, seeded_session):
    student = headers_for(client, seeded_session, "student")
    body = ask(client, student, "Which courses are in this semester?", program_id="PROG-BTECH-IT-001",
               semester_id="SEM-BTECH-IT-06")
    assert body["route"] == "structured" and "2CEIT602" in body["answer"]
    assert any("selected context" in reason for reason in body["reasons"])
    assert client.post(f"{API}/chat/query", headers=student,
                       json={"question": "x y", "semester_id": "sem; drop table"}).status_code == 422


def test_history_is_personal_and_analytics_is_for_admins(client, seeded_session):
    alice, bob = headers_for(client, seeded_session, "student"), headers_for(client, seeded_session, "student")
    ask(client, alice, "What is the hostel curfew time?")
    ask(client, alice, "What grade do I get for 85 marks?")
    history = client.get(f"{API}/chat/history", headers=alice).json()
    assert [h["question"] for h in history][:2] == ["What grade do I get for 85 marks?", "What is the hostel curfew time?"]
    assert [h["question"] for h in client.get(f"{API}/chat/history", params={"q": "curfew"}, headers=alice).json()] == [
        "What is the hostel curfew time?"]
    assert client.get(f"{API}/chat/history", headers=bob).json() == []

    assert client.get(f"{API}/chat/analytics", headers=alice).status_code == 403
    stats = client.get(f"{API}/chat/analytics", headers=headers_for(client, seeded_session, "admin")).json()
    assert stats["total_questions"] >= 2 and len(stats["last_7_days"]) == 7
    assert "What is the hostel curfew time?" in [q["question"] for q in stats["unanswered"]]
    assert "user_id" not in str(stats)


# --- content, sources, system info ------------------------------------------------------------------

def test_policies_notices_calendar_and_sources_are_labelled(client, seeded_session):
    student = headers_for(client, seeded_session, "student")
    policies = client.get(f"{API}/policies", headers=student).json()
    notices = client.get(f"{API}/notices", params={"limit": 5}, headers=student).json()
    calendar = client.get(f"{API}/calendar", params={"semester_id": "SEM-BTECH-IT-06"}, headers=student).json()
    sources = client.get(f"{API}/knowledge/sources", headers=student).json()
    assert policies and all(p["provenance"]["source_type"] == "synthetic" for p in policies)
    assert len(notices) == 5 and notices[0]["notice_date"] >= notices[-1]["notice_date"]
    assert calendar and all("SEM-BTECH-IT-06" in e["semester_ids"] for e in calendar)
    assert {"DOC-OFFICIAL-SYLLABUS-001", "DOC-OFFICIAL-CATALOG-001"} <= {s["document_id"] for s in sources}
    assert {s["source_type"] for s in sources} == {"official", "synthetic"}


def test_system_info_for_logged_in_users_only(client, seeded_session):
    assert client.get(f"{API}/system/info").status_code == 401
    info = client.get(f"{API}/system/info", headers=headers_for(client, seeded_session, "student")).json()
    assert info["generation_provider"] == "extractive" and info["vector_store"] == "Chroma (embedded)"
    assert "password" not in str(info).lower()
