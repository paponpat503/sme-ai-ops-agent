from app.security.context import DEFAULT_PRINCIPAL
from app.security.context import PrincipalContext
from app.tools.transport import MCPToolTransport


def test_real_mcp_stdio_tool_call():
    response = MCPToolTransport().call("get_open_tickets", {"customer_id": "C003"}, DEFAULT_PRINCIPAL)
    assert response.error is None
    assert response.error_code is None
    assert isinstance(response.result, list)
    assert {item["ticket_id"] for item in response.result} >= {"T1002", "T1003"}


def test_real_mcp_stdio_propagates_tenant_identity():
    other = PrincipalContext("other", "viewer", frozenset({"viewer"}), "mcp-test")
    response = MCPToolTransport().call("get_open_tickets", {}, other)
    assert response.error is None
    assert response.error_code is None
    assert response.result == []


def test_real_mcp_stdio_returns_controlled_argument_error():
    response = MCPToolTransport().call(
        "search_policy_docs",
        {"query": "refund", "top_k": 99},
        DEFAULT_PRINCIPAL,
    )
    assert response.result is None
    assert response.error
