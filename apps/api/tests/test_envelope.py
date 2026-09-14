from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_envelope():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"
    assert body["request_id"]
    assert res.headers["X-Request-Id"] == body["request_id"]


def test_request_id_differs_between_requests():
    first = client.get("/health").json()["request_id"]
    second = client.get("/health").json()["request_id"]
    assert first != second


def test_sql_guard_rejected_in_envelope():
    res = client.post("/api/v1/sql/preview", json={"sql": "DROP TABLE t"})
    assert res.status_code == 400
    body = res.json()
    assert body["code"] == 40001
    assert body["message"]
    assert body["data"] is None
    assert body["request_id"]


def test_validation_error_in_envelope():
    res = client.post("/api/v1/sql/preview", json={})
    assert res.status_code == 422
    body = res.json()
    assert body["code"] == 40000
    assert "sql" in body["message"]
    assert body["request_id"]


def test_not_found_in_envelope():
    res = client.get("/definitely-not-a-route")
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == 40400
    assert body["request_id"]


def test_aiqa_ask_guards_provided_sql():
    res = client.post(
        "/api/v1/aiqa/sessions/s1/ask",
        json={"question": "订单量", "sql": "DELETE FROM orders"},
    )
    assert res.status_code == 400
    assert res.json()["code"] == 40001


def test_aiqa_ask_validates_question():
    res = client.post("/api/v1/aiqa/sessions/s1/ask", json={})
    assert res.status_code == 422
    assert res.json()["code"] == 40000
