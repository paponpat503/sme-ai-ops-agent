from app.security.context import PrincipalContext
from app.tools.registry import call_registered_tool


def test_demo_task_retries_are_idempotent():
    operator = PrincipalContext("demo", "operator", frozenset({"operator"}), "test")
    arguments = {
        "customer_id": "C001",
        "task": "Schedule support call",
        "due_date": "2026-08-01",
        "idempotency_key": "portfolio-test-001",
    }
    first = call_registered_tool("create_crm_task_demo", arguments, operator)
    second = call_registered_tool("create_crm_task_demo", arguments, operator)
    assert first.error is None
    assert first.result == second.result
    assert first.result["task_id"].startswith("TASK-")
