import pytest
from fastapi.testclient import TestClient

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
ME_URL = "/auth/me"

VALID_USER = {"name": "Alice", "email": "alice@example.com", "password": "secret123"}


def test_register_returns_token(client: TestClient):
    r = client.post(REGISTER_URL, json=VALID_USER)
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email_returns_400(client: TestClient):
    client.post(REGISTER_URL, json=VALID_USER)
    r = client.post(REGISTER_URL, json=VALID_USER)
    assert r.status_code == 400


def test_register_weak_password_returns_422(client: TestClient):
    r = client.post(REGISTER_URL, json={**VALID_USER, "email": "b@b.com", "password": "short"})
    assert r.status_code == 422


def test_register_empty_name_returns_422(client: TestClient):
    r = client.post(REGISTER_URL, json={**VALID_USER, "email": "c@c.com", "name": "   "})
    assert r.status_code == 422


def test_login_success_returns_token(client: TestClient):
    client.post(REGISTER_URL, json=VALID_USER)
    r = client.post(LOGIN_URL, json={"email": VALID_USER["email"], "password": VALID_USER["password"]})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_returns_401(client: TestClient):
    client.post(REGISTER_URL, json=VALID_USER)
    r = client.post(LOGIN_URL, json={"email": VALID_USER["email"], "password": "wrongpassword"})
    assert r.status_code == 401


def test_login_unknown_email_returns_401(client: TestClient):
    r = client.post(LOGIN_URL, json={"email": "nobody@example.com", "password": "secret123"})
    assert r.status_code == 401


def test_me_returns_user_info(client: TestClient):
    reg = client.post(REGISTER_URL, json={**VALID_USER, "email": "me@example.com"})
    token = reg.json()["access_token"]
    r = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "me@example.com"
    assert data["name"] == VALID_USER["name"]
    assert "id" in data


def test_me_without_token_returns_401(client: TestClient):
    r = client.get(ME_URL)
    assert r.status_code == 401
