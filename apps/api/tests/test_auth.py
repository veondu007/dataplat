import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture()
def auth_token() -> str:
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["data"]["token"]


def test_protected_route_without_token():
    res = client.get("/api/v1/assets/overview")
    assert res.status_code == 401
    body = res.json()
    assert body["code"] == 40100
    assert body["request_id"]


def test_login_wrong_password():
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["code"] == 40100


def test_login_ok_returns_token():
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0
    assert body["data"]["token"]
    assert body["data"]["user"]["username"] == "admin"


def test_protected_route_with_token(auth_token):
    res = client.get("/api/v1/assets/overview", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200
    assert res.json()["code"] == 0


def test_auth_me(auth_token):
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200
    assert res.json()["data"]["username"] == "admin"


def test_forged_token_rejected():
    res = client.get("/api/v1/assets/overview", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401
    assert res.json()["code"] == 40100


def test_health_is_public():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["code"] == 0
