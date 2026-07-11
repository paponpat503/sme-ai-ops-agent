from app.security.context import PrincipalContext
from app.tools.registry import call_registered_tool


def test_explicit_principal_is_propagated_to_repository_context():
    other = PrincipalContext("other", "user", frozenset({"viewer"}), "test")
    response = call_registered_tool("search_customers", {"query": ""}, other)
    assert response.error is None
    assert response.result == []


def test_explicit_principal_is_propagated_to_retrieval_context():
    other = PrincipalContext("other", "user", frozenset({"viewer"}), "test")
    response = call_registered_tool("search_policy_docs", {"query": "refund"}, other)
    assert response.error is None
    assert response.result == []
