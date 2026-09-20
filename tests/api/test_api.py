from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from kynka.presentation.api import create_app
from kynka.presentation.api.config import APISettings

@pytest.fixture()
def client(tmp_path: Path):
    database = tmp_path / "kynka-test.db"
    app = create_app(
        APISettings(memory_size=20, session_ttl_minutes=30),
        database_path=database,
    )
    with TestClient(app) as c:
        yield c

@pytest.fixture()
def admin_headers(client):
    r = client.post("/api/v1/auth/bootstrap", json={
        "organization_name": "Kynka Test",
        "name": "Admin Test",
        "email": "admin@test.local",
        "password": "TesteKynka2026!",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_platform_health_and_ready(client):
    health = client.get("/api/v1/platform/health")
    ready = client.get("/api/v1/platform/ready")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"]["database"] is True
    assert ready.json()["checks"]["migrations"] is True

def test_private_endpoint_requires_authentication(client):
    assert client.get("/api/v1/auth/me").status_code == 401

def test_request_id_is_returned(client):
    r = client.get("/api/v1/platform/health", headers={"X-Request-ID": "quality-47-50"})
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "quality-47-50"
    assert "X-Response-Time-Ms" in r.headers

def test_simple_chat(client, admin_headers):
    r = client.post("/api/v1/chat", json={"message": "Some 10 mais 5"}, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["result"] == 15
    assert body["mode"] == "simple"

def test_plan_chat(client, admin_headers):
    r = client.post("/api/v1/chat", json={
        "message": "Some 10 mais 5, depois multiplique o resultado por 3 e depois some 5"
    }, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["result"] == 50
    assert body["mode"] == "plan"
    assert len(body["steps"]) == 3

def test_session_context(client, admin_headers):
    first = client.post("/api/v1/chat", json={"message": "Some 10 mais 5"}, headers=admin_headers)
    assert first.status_code == 200, first.text
    second = client.post("/api/v1/chat", json={
        "session_id": first.json()["session_id"],
        "message": "Multiplique esse resultado por 3",
    }, headers=admin_headers)
    assert second.status_code == 200, second.text
    assert second.json()["success"] is True
    assert second.json()["result"] == 45

def test_database_is_isolated(client):
    path = Path(client.app.state.database_path)
    assert path.name == "kynka-test.db"
    assert path.exists()
