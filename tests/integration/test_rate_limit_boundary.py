from fastapi.testclient import TestClient

from app import main
from app.config import get_settings


def test_api_rate_limit_returns_headers(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_MAX_CLIENTS", "100")
    get_settings.cache_clear()
    monkeypatch.setattr(main, "_rate_limiter", None)
    try:
        client = TestClient(main.app)
        first = client.get("/tools/list")
        second = client.get("/tools/list")
        blocked = client.get("/tools/list")
        assert first.status_code == second.status_code == 200
        assert first.headers["X-RateLimit-Limit"] == "2"
        assert second.headers["X-RateLimit-Remaining"] == "0"
        assert blocked.status_code == 429
        assert int(blocked.headers["Retry-After"]) >= 1
    finally:
        get_settings.cache_clear()
        main._rate_limiter = None


def test_health_and_static_routes_do_not_consume_api_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_MAX_CLIENTS", "100")
    get_settings.cache_clear()
    monkeypatch.setattr(main, "_rate_limiter", None)
    try:
        client = TestClient(main.app)
        assert client.get("/live").status_code == 200
        assert client.get("/live").status_code == 200
        assert client.get("/tools/list").status_code == 200
        assert client.get("/tools/list").status_code == 429
    finally:
        get_settings.cache_clear()
        main._rate_limiter = None
