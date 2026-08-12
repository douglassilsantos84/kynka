from fastapi.testclient import TestClient
from kynka.presentation.api import create_app
from kynka.presentation.api.config import APISettings

def client():
    return TestClient(create_app(APISettings(memory_size=20, session_ttl_minutes=30)))

def test_health():
    with client() as c:
        r = c.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

def test_simple_chat():
    with client() as c:
        body = c.post("/api/v1/chat", json={"message": "Some 10 mais 5"}).json()
        assert body["success"] is True
        assert body["result"] == 15
        assert body["mode"] == "simple"

def test_plan_chat():
    with client() as c:
        body = c.post("/api/v1/chat", json={"message": "Some 10 mais 5, depois multiplique o resultado por 3 e depois some 5"}).json()
        assert body["success"] is True
        assert body["result"] == 50
        assert body["mode"] == "plan"
        assert len(body["steps"]) == 3

def test_session_context():
    with client() as c:
        first = c.post("/api/v1/chat", json={"message": "Some 10 mais 5"}).json()
        second = c.post("/api/v1/chat", json={"session_id": first["session_id"], "message": "Multiplique esse resultado por 3"}).json()
        assert second["success"] is True
        assert second["result"] == 45
