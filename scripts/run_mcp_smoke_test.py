from __future__ import annotations

from app.tools.registry import TOOL_REGISTRY, call_registered_tool, list_registered_tools
from rich import print_json


EXPECTED_TOOLS = {
    "search_customers",
    "get_customer_profile",
    "get_open_tickets",
    "get_overdue_orders",
    "get_recent_notes",
    "search_policy_docs",
    "draft_followup_email",
    "create_crm_task_demo",
}


def run_smoke_test() -> None:
    registered = set(TOOL_REGISTRY)
    missing = sorted(EXPECTED_TOOLS - registered)
    print(f"registered_tools: {len(registered)}")
    print_json(data=list_registered_tools())
    if missing:
        raise SystemExit(f"Missing expected tools: {missing}")

    open_tickets = call_registered_tool("get_open_tickets", {"customer_id": "C003"})
    if open_tickets.error or not open_tickets.result:
        raise SystemExit(f"get_open_tickets failed: {open_tickets.error}")

    policy_hits = call_registered_tool("search_policy_docs", {"query": "refund policy", "top_k": 2})
    if policy_hits.error or not policy_hits.result:
        raise SystemExit(f"search_policy_docs failed: {policy_hits.error}")

    print("get_open_tickets: PASS")
    print_json(data=open_tickets.model_dump())
    print("search_policy_docs: PASS")
    print_json(data=policy_hits.model_dump())


if __name__ == "__main__":
    run_smoke_test()
