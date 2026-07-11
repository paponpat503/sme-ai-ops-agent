from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_request_id_is_returned():
    response = TestClient(app).get("/live", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"


def test_invalid_request_id_is_replaced():
    response = TestClient(app).get("/live", headers={"X-Request-ID": "bad request value"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad request value"
    assert len(response.headers["X-Request-ID"]) == 36


def test_actual_request_body_limit_is_enforced(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "1024")
    get_settings.cache_clear()
    try:
        response = TestClient(app).post(
            "/agent/ask",
            content=b'{"question":"' + b"x" * 2000 + b'"}',
            headers={"Content-Type": "application/json", "Content-Length": "100"},
        )
        assert response.status_code == 413
    finally:
        get_settings.cache_clear()


def test_readiness_reports_ready():
    with TestClient(app) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["checks"] == {"retrieval": True, "data": True, "tool_transport": True}


def test_production_requires_api_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_API_KEY", "secret")
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        assert client.get("/tools/list").status_code == 401
        assert client.get("/tools/list", headers={"Authorization": "Bearer secret"}).status_code == 200
    finally:
        get_settings.cache_clear()


def test_production_identity_enforces_tenant_and_role(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_API_KEY", raising=False)
    monkeypatch.setenv(
        "APP_API_KEYS_JSON",
        '{"viewer-key":{"tenant_id":"other","user_id":"u2","roles":["viewer"]}}',
    )
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        headers = {"Authorization": "Bearer viewer-key"}
        customers = client.post(
            "/tools/call",
            headers=headers,
            json={"tool_name": "search_customers", "arguments": {"query": ""}},
        ).json()
        assert customers["result"] == []
        write_response = client.post(
            "/tools/call",
            headers=headers,
            json={"tool_name": "create_crm_task_demo", "arguments": {"customer_id":"C001","task":"Call","due_date":"2026-08-01"}},
        )
        assert write_response.status_code == 403
        write = write_response.json()
        assert "Forbidden" in write["error"]
        assert write["error_code"] == "forbidden"
    finally:
        get_settings.cache_clear()
