from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_docs_available():
    assert client.get("/docs").status_code == 200
    assert "/api/v1/system/health" in client.get("/openapi.json").json()["paths"]


def test_unknown_route_is_404():
    assert client.get("/api/v1/does-not-exist").status_code == 404
