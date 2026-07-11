from fastapi.testclient import TestClient

from app import main


class UnavailableRepository:
    def is_ready(self):
        return False


def test_readiness_reports_failed_data_dependency(monkeypatch):
    monkeypatch.setattr(main, "get_business_repository", lambda: UnavailableRepository())
    with TestClient(main.app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert "data" in response.json()["failed_dependencies"]


def test_readiness_reports_failed_tool_transport(monkeypatch):
    monkeypatch.setattr(main, "tool_transport_is_ready", lambda _: False)
    with TestClient(main.app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert "tool_transport" in response.json()["failed_dependencies"]
