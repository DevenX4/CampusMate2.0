"""Authentication (who are you?) and authorization (what may you do?)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.db import get_db
from app.core.security import hash_password, token_digest, verify_password
from app.main import app
from app.models.auth import User
from app.models.operations import AuditLog
from app.schemas.users import UserCreate
from app.services import users
from app.services.audit import RequestContext

API = "/api/v1"
PASSWORD = "correct-horse-battery"


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def make_user(db, email: str, role: str) -> User:
    out = users.create_user(db, UserCreate(email=email, full_name=email.split("@")[0],
                                           password=PASSWORD, role=role),
                            actor_id=None, context=RequestContext())
    return db.get(User, out.id)


@pytest.fixture
def admin(db_session):
    return make_user(db_session, "admin@campusmate-demo.example", "admin")


@pytest.fixture
def student(db_session):
    return make_user(db_session, "student@campusmate-demo.example", "student")


def login(client, email: str, password: str = PASSWORD):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


def bearer(client, email: str) -> dict:
    return {"Authorization": f"Bearer {login(client, email).json()['access_token']}"}


# --- password hashing ------------------------------------------------------------------

def test_password_hash_is_salted_and_verifiable():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first != second and first.startswith("$argon2id$")  # random salt each time
    assert verify_password(first, PASSWORD)
    assert not verify_password(first, "wrong-password")
    assert not verify_password(None, PASSWORD)  # unknown user never verifies


# --- login / me / logout -----------------------------------------------------------------

def test_login_returns_token_and_sets_httponly_cookie(client, student):
    response = login(client, "student@campusmate-demo.example")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "student" and body["token_type"] == "bearer"
    assert "password" not in response.text and "argon2" not in response.text
    cookie = response.headers["set-cookie"]
    assert "campusmate_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie


def test_login_is_case_insensitive_on_email(client, student):
    assert login(client, "STUDENT@CampusMate-Demo.example").status_code == 200


@pytest.mark.parametrize("email,password", [
    ("student@campusmate-demo.example", "wrong-password"),  # wrong password
    ("nobody@campusmate-demo.example", PASSWORD),           # unknown email
])
def test_failed_login_gives_the_same_vague_answer(client, student, email, password):
    response = login(client, email, password)
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password."


def test_deactivated_account_cannot_log_in(client, db_session, student):
    student.is_active = False
    db_session.flush()
    assert login(client, "student@campusmate-demo.example").status_code == 401


def test_me_works_with_bearer_token_and_with_cookie(client, student):
    headers = bearer(client, "student@campusmate-demo.example")
    me = client.get(f"{API}/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["permissions"] == ["catalog:read", "chat:use"]
    # The TestClient kept the cookie from the login, as a browser would.
    assert client.get(f"{API}/auth/me").status_code == 200


def test_me_without_credentials_is_401_with_challenge(client):
    response = client.get(f"{API}/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "unauthorized"


def test_logout_revokes_the_token_immediately(client, student):
    headers = bearer(client, "student@campusmate-demo.example")
    assert client.post(f"{API}/auth/logout", headers=headers).status_code == 204
    client.cookies.clear()
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401


def test_expired_session_is_rejected(client, db_session, student):
    token = login(client, "student@campusmate-demo.example").json()["access_token"]
    client.cookies.clear()
    past = datetime.now(UTC) - timedelta(hours=1)
    db_session.execute(text("UPDATE user_sessions SET created_at = :c, expires_at = :e WHERE token_sha256 = :t"),
                       {"c": past - timedelta(hours=1), "e": past, "t": token_digest(token)})
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_only_token_hash_is_stored(client, db_session, student):
    token = login(client, "student@campusmate-demo.example").json()["access_token"]
    stored = db_session.scalar(text("SELECT token_sha256 FROM user_sessions"))
    assert stored == token_digest(token) and stored != token


# --- authorization ---------------------------------------------------------------------------

def test_admin_endpoints_are_401_anonymous_403_student_200_admin(client, admin, student):
    assert client.get(f"{API}/users").status_code == 401
    assert client.get(f"{API}/users", headers=bearer(client, "student@campusmate-demo.example")).status_code == 403
    client.cookies.clear()
    assert client.get(f"{API}/users", headers=bearer(client, "admin@campusmate-demo.example")).status_code == 200


def test_catalog_stays_public_for_guests(client):
    assert client.get(f"{API}/courses").status_code == 200


def test_student_cannot_create_users_or_make_themselves_admin(client, student):
    headers = bearer(client, "student@campusmate-demo.example")
    response = client.post(f"{API}/users", headers=headers, json={
        "email": "x@campusmate-demo.example", "password": PASSWORD, "role": "admin"})
    assert response.status_code == 403


def test_admin_creates_users_and_duplicates_conflict(client, admin):
    headers = bearer(client, "admin@campusmate-demo.example")
    body = {"email": "new.faculty@campusmate-demo.example", "password": PASSWORD, "role": "faculty"}
    created = client.post(f"{API}/users", headers=headers, json=body)
    assert created.status_code == 201 and created.json()["role"] == "faculty"
    duplicate = client.post(f"{API}/users", headers=headers, json={**body, "email": "NEW.faculty@campusmate-demo.example"})
    assert duplicate.status_code == 409


def test_guest_role_cannot_be_assigned_and_short_passwords_rejected(client, admin):
    headers = bearer(client, "admin@campusmate-demo.example")
    assert client.post(f"{API}/users", headers=headers, json={
        "email": "g@campusmate-demo.example", "password": PASSWORD, "role": "guest"}).status_code == 422
    assert client.post(f"{API}/users", headers=headers, json={
        "email": "s@campusmate-demo.example", "password": "short", "role": "student"}).status_code == 422


def test_admin_cannot_lock_themselves_out(client, admin):
    headers = bearer(client, "admin@campusmate-demo.example")
    for change in ({"is_active": False}, {"role": "student"}):
        assert client.patch(f"{API}/users/{admin.id}", headers=headers, json=change).status_code == 409


def test_deactivating_a_user_ends_their_sessions(client, admin, student):
    student_headers = bearer(client, "student@campusmate-demo.example")
    client.cookies.clear()
    admin_headers = bearer(client, "admin@campusmate-demo.example")
    client.cookies.clear()
    assert client.patch(f"{API}/users/{student.id}", headers=admin_headers,
                        json={"is_active": False}).status_code == 200
    assert client.get(f"{API}/auth/me", headers=student_headers).status_code == 401


# --- audit trail -----------------------------------------------------------------------------

def test_logins_and_user_changes_are_audited_without_secrets(client, db_session, admin, student):
    login(client, "student@campusmate-demo.example", "wrong-password")
    headers = bearer(client, "admin@campusmate-demo.example")
    client.patch(f"{API}/users/{student.id}", headers=headers, json={"password": "another-long-password"})

    entries = db_session.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    actions = [e.action for e in entries]
    assert {"user.create", "auth.login_failed", "auth.login", "user.update"} <= set(actions)
    update = next(e for e in entries if e.action == "user.update")
    assert update.details == {"password": "changed"} and update.actor_user_id == admin.id
    assert all("another-long-password" not in str(e.details) and PASSWORD not in str(e.details) for e in entries)


def test_audit_log_api_is_admin_only(client, admin, student):
    assert client.get(f"{API}/audit-logs", headers=bearer(client, "student@campusmate-demo.example")).status_code == 403
    client.cookies.clear()
    page = client.get(f"{API}/audit-logs", headers=bearer(client, "admin@campusmate-demo.example")).json()
    assert page["items"][0]["action"] == "auth.login"  # newest first


def test_every_response_has_a_request_id(client):
    assert len(client.get(f"{API}/system/health").headers["x-request-id"]) == 32
    echoed = client.get(f"{API}/system/health", headers={"X-Request-ID": "trace-12345678"})
    assert echoed.headers["x-request-id"] == "trace-12345678"
