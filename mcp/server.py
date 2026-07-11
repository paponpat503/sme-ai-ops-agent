from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.tools.registry import call_registered_tool
from app.security.context import PrincipalContext


def _mcp_principal() -> PrincipalContext:
    return PrincipalContext(
        tenant_id=os.getenv("MCP_TENANT_ID", "demo"),
        user_id=os.getenv("MCP_USER_ID", "mcp-client"),
        roles=frozenset(role for role in os.getenv("MCP_ROLES", "operator").split(",") if role),
        request_id=os.getenv("MCP_REQUEST_ID", "mcp-local"),
    )


def _result_or_raise(tool_name: str, arguments: dict[str, Any]) -> Any:
    response = call_registered_tool(tool_name, arguments, _mcp_principal())
    if response.error:
        raise ValueError(response.error)
    return response.result


def create_mcp_server() -> Any:
    if FastMCP is None:
        raise RuntimeError("MCP SDK is not installed. Run: py -m pip install -r requirements.txt")

    server = FastMCP("sme-ai-ops-agent")

    @server.tool()
    def search_customers(query: str) -> list[dict[str, Any]]:
        """Search CRM customer records by text."""
        return _result_or_raise("search_customers", {"query": query})

    @server.tool()
    def get_customer_profile(customer_id: str) -> dict[str, Any]:
        """Get one CRM customer profile by customer_id."""
        return _result_or_raise("get_customer_profile", {"customer_id": customer_id})

    @server.tool()
    def get_open_tickets(customer_id: str | None = None) -> list[dict[str, Any]]:
        """List open support tickets, optionally filtered by customer_id."""
        return _result_or_raise("get_open_tickets", {"customer_id": customer_id})

    @server.tool()
    def get_overdue_orders(customer_id: str | None = None) -> list[dict[str, Any]]:
        """List overdue orders, optionally filtered by customer_id."""
        return _result_or_raise("get_overdue_orders", {"customer_id": customer_id})

    @server.tool()
    def get_recent_notes(customer_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """List recent CRM notes, optionally filtered by customer_id."""
        return _result_or_raise("get_recent_notes", {"customer_id": customer_id, "limit": limit})

    @server.tool()
    def search_policy_docs(query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Search company policy and onboarding documents."""
        return _result_or_raise("search_policy_docs", {"query": query, "top_k": top_k})

    @server.tool()
    def draft_followup_email(customer_name: str, reason: str, action: str) -> str:
        """Draft a customer follow-up email."""
        return _result_or_raise(
            "draft_followup_email",
            {"customer_name": customer_name, "reason": reason, "action": action},
        )

    @server.tool()
    def create_crm_task_demo(
        customer_id: str,
        task: str,
        due_date: str,
        owner: str = "sales",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a demo CRM task payload without writing to a real CRM."""
        return _result_or_raise(
            "create_crm_task_demo",
            {"customer_id": customer_id, "task": task, "due_date": due_date, "owner": owner, "idempotency_key": idempotency_key},
        )

    return server


mcp = create_mcp_server() if FastMCP is not None else None


if __name__ == "__main__":
    if mcp is None:
        sys.stderr.write("MCP SDK is not installed. Run: py -m pip install -r requirements.txt\n")
        raise SystemExit(1)
    mcp.run()
