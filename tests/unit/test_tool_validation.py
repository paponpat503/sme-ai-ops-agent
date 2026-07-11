from app.security.context import PrincipalContext
from app.tools.registry import call_registered_tool


def test_extra_arguments_are_rejected():
    result = call_registered_tool("get_open_tickets", {"unexpected": 1})
    assert result.error and "extra" in result.error.lower()
    assert result.error_code == "invalid_arguments"


def test_argument_bounds_are_enforced():
    result = call_registered_tool("search_policy_docs", {"query": "refund", "top_k": 99})
    assert result.error
    assert result.error_code == "invalid_arguments"


def test_capability_is_enforced():
    principal = PrincipalContext("demo", "viewer", frozenset({"viewer"}), "test")
    result = call_registered_tool(
        "create_crm_task_demo",
        {"customer_id": "C001", "task": "Call", "due_date": "2026-08-01"},
        principal,
    )
    assert result.error and "Forbidden" in result.error
    assert result.error_code == "forbidden"
