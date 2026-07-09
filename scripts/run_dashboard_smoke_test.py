from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


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
    client = TestClient(app)

    demo = client.get("/demo")
    _assert(demo.status_code == 200, f"/demo returned {demo.status_code}")
    _assert("SME AI Ops Agent" in demo.text, "/demo did not include dashboard title")

    tools = client.get("/tools/list")
    _assert(tools.status_code == 200, f"/tools/list returned {tools.status_code}")
    tool_names = {tool["name"] for tool in tools.json().get("tools", [])}
    _assert(EXPECTED_TOOLS.issubset(tool_names), f"/tools/list missing tools: {EXPECTED_TOOLS - tool_names}")

    agent = client.post("/agent/ask", json={"question": "Which customers need follow-up today?"})
    _assert(agent.status_code == 200, f"/agent/ask returned {agent.status_code}")
    payload = agent.json()
    _assert("answer" in payload, "/agent/ask missing answer wrapper")
    _assert("metadata" in payload, "/agent/ask missing metadata wrapper")
    _assert(payload["answer"]["actions"], "/agent/ask returned no customer actions")

    print("/demo: PASS")
    print("/tools/list: PASS")
    print("/agent/ask: PASS")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    run_smoke_test()
