"""Abuse limits and protective defaults: login throttling, the chat rate limit, security
headers, the request body limit, the production guard and session clean-up."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select, update

from app.api.routes import auth as auth_routes
from app.api.routes import chat as chat_routes
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.generation.extractive import ExtractiveProvider
from app.generation.runtime import get_generator
from app.main import app
from app.models.auth import UserSession
from app.models.operations import AuditLog
from app.retrieval.runtime import get_bm25_cache, get_embedder, get_vector_index
from app.retrieval.search import Bm25Cache
from app.schemas.users import UserCreate
from app.services import auth, users
from app.services.audit import RequestContext
from tests.helpers import API, PASSWORD, headers_for


def settings_with(**overrides) -> Settings:
    return get_settings().model_copy(update=overrides)


@pytest.fixture
def client(db_session, indexer):
    app.dependency_overrides.update({get_db: lambda: db_session, get_embedder: lambda: indexer.embedder,
                                     get_vector_index: lambda: indexer.index, get_bm25_cache: Bm25Cache,
                                     get_generator: ExtractiveProvider})
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def account(db, email: str):
    return users.create_user(db, UserCreate(email=email, password=PASSWORD, role="student"), actor_id=None,
                             context=RequestContext())


def login(client, email: str, password: str):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


# --- login throttling -------------------------------------------------------------------------

def test_repeated_failures_lock_the_account_even_for_the_right_password(client, db_session, monkeypatch):
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings_with(login_max_failures=3, login_window_minutes=15))
    account(db_session, "target@campusmate-demo.example")
    for _ in range(3):
        assert login(client, "target@campusmate-demo.example", "wrong-guess").status_code == 401
    locked = login(client, "target@campusmate-demo.example", PASSWORD)
    assert locked.status_code == 429 and int(locked.headers["Retry-After"]) > 0
    assert locked.json()["error"]["code"] == "rate_limited"
    throttled = select(func.count()).select_from(AuditLog).where(AuditLog.action == "auth.login_throttled")
    assert db_session.scalar(throttled) == 1

    # Once the failures have left the window, the right password works again.
    later = auth._now() + timedelta(minutes=16)
    monkeypatch.setattr(auth, "_now", lambda: later)
    assert login(client, "target@campusmate-demo.example", PASSWORD).status_code == 200


def test_one_client_trying_many_accounts_is_throttled(client, db_session, monkeypatch):
    monkeypatch.setattr(auth_routes, "get_settings",
                        lambda: settings_with(login_max_failures=10, login_max_failures_per_ip=4))
    spray = TestClient(app, client=("203.0.113.9", 50000))  # a real client address (TEST-NET-3)
    for i in range(4):
        assert login(spray, f"guess{i}@campusmate-demo.example", "password1").status_code == 401
    assert login(spray, "someone-else@campusmate-demo.example", "password1").status_code == 429
    elsewhere = TestClient(app, client=("198.51.100.7", 50000))
    assert login(elsewhere, "someone-else@campusmate-demo.example", "password1").status_code == 401


def test_failures_of_another_account_do_not_lock_mine(client, db_session, monkeypatch):
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings_with(login_max_failures=2))
    account(db_session, "mine@campusmate-demo.example")
    for _ in range(2):
        login(client, "other@campusmate-demo.example", "wrong")
    assert login(client, "mine@campusmate-demo.example", PASSWORD).status_code == 200


# --- chat rate limit ------------------------------------------------------------------------------

def test_chat_is_rate_limited_per_user(client, db_session, monkeypatch):
    monkeypatch.setattr(chat_routes, "get_settings", lambda: settings_with(chat_questions_per_minute=2))
    student = headers_for(client, db_session, "student")
    other = headers_for(client, db_session, "student")
    ask = lambda headers: client.post(f"{API}/chat/query", json={"question": "What is the hostel curfew?"}, headers=headers)
    assert [ask(student).status_code for _ in range(2)] == [200, 200]
    limited = ask(student)
    assert limited.status_code == 429 and 0 < int(limited.headers["Retry-After"]) <= 61
    assert ask(other).status_code == 200  # a per-user limit


# --- protective defaults ---------------------------------------------------------------------------

def test_api_responses_carry_security_headers(client):
    headers = client.get(f"{API}/system/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Request-ID"]


def test_oversized_json_bodies_are_refused(client, db_session):
    student = headers_for(client, db_session, "student")
    huge = {"question": "x" * (get_settings().max_body_kb * 1024 + 10)}
    response = client.post(f"{API}/chat/query", json=huge, headers=student)
    assert response.status_code == 413 and response.json()["error"]["code"] == "body_too_large"

    def chunks():  # no Content-Length: the limit is enforced while reading
        for _ in range(get_settings().max_body_kb + 2):
            yield b"x" * 1024
    streamed = client.post(f"{API}/chat/query", content=chunks(), headers={**student, "Content-Type": "application/json"})
    assert streamed.status_code == 413


def test_production_requires_secure_cookies():
    with pytest.raises(ValidationError, match="COOKIE_SECURE must be true"):
        Settings(_env_file=None, db_password="x", app_env="production", cookie_secure=False)
    assert Settings(_env_file=None, db_password="x", app_env="production", cookie_secure=True).cookie_secure


def test_dead_sessions_are_purged(client, db_session):
    user = account(db_session, "sessions@campusmate-demo.example")
    first = login(client, "sessions@campusmate-demo.example", PASSWORD).json()["access_token"]
    login(client, "sessions@campusmate-demo.example", PASSWORD)
    client.post(f"{API}/auth/logout", headers={"Authorization": f"Bearer {first}"})  # revoked
    db_session.execute(update(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
                       .values(expires_at=auth._now() - timedelta(minutes=1), created_at=auth._now() - timedelta(hours=1)))
    assert auth.purge_sessions(db_session) == 2
    assert db_session.scalar(select(func.count()).select_from(UserSession).where(UserSession.user_id == user.id)) == 0
