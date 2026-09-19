from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes import system
from app.core.db import expected_schema_revision, get_db
from app.main import app

client = TestClient(app)
READY = "/api/v1/system/ready"


def test_health_returns_ok():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_docs_available():
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/api/v1/system/health", READY} <= set(paths)


def test_unknown_route_is_404():
    assert client.get("/api/v1/does-not-exist").status_code == 404


def test_ready_when_database_is_migrated(migrated_engine):
    response = client.get(READY)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready" and body["database"] == "ok"
    assert body["schema_revision"] == expected_schema_revision() is not None


def test_not_ready_when_schema_is_behind(migrated_engine, monkeypatch):
    monkeypatch.setattr(system, "current_schema_revision", lambda db: "an_old_revision")
    response = client.get(READY)
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_not_ready_when_database_is_unreachable():
    # Nothing listens on port 1, so every query fails to connect.
    dead_engine = create_engine(
        "postgresql+psycopg://nobody:x@127.0.0.1:1/none", connect_args={"connect_timeout": 2}
    )

    def unreachable_db():
        with Session(dead_engine) as session:
            yield session

    app.dependency_overrides[get_db] = unreachable_db
    try:
        response = client.get(READY)
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"
