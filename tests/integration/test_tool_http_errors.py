from fastapi.testclient import TestClient

from app.main import app


def test_unknown_tool_returns_404_envelope():
    response = TestClient(app).post("/tools/call", json={"tool_name": "missing", "arguments": {}})
    assert response.status_code == 404
    assert response.json()["error_code"] == "unknown_tool"


def test_invalid_tool_arguments_return_422_envelope():
    response = TestClient(app).post(
        "/tools/call",
        json={"tool_name": "search_policy_docs", "arguments": {"query": "refund", "top_k": 99}},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_arguments"


def test_successful_tool_call_has_no_error_code():
    response = TestClient(app).post(
        "/tools/call",
        json={"tool_name": "get_open_tickets", "arguments": {"customer_id": "C003"}},
    )
    assert response.status_code == 200
    assert response.json()["error_code"] is None
