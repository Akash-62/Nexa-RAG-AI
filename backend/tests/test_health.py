from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_docs_reachable(client: TestClient):
    r = client.get("/docs")
    assert r.status_code == 200


def test_protected_route_without_token_returns_401(client: TestClient):
    r = client.get("/documents")
    assert r.status_code == 401


def test_protected_route_with_bad_token_returns_401(client: TestClient):
    r = client.get("/documents", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
