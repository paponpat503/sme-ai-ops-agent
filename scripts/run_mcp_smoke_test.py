from __future__ import annotations

import json
import sys
from pathlib import Path

import anyio
from app.tools.registry import list_registered_tools


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


async def run_smoke_test() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(root / "mcp" / "server.py")],
        cwd=root,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            missing = EXPECTED_TOOLS - names
            if missing:
                raise SystemExit(f"MCP list_tools missing: {sorted(missing)}")
            registry = {tool["name"]: tool for tool in list_registered_tools()}
            for tool in listed.tools:
                mcp_schema = tool.inputSchema
                registry_schema = registry[tool.name]["input_schema"]
                if set(mcp_schema.get("properties", {})) != set(registry_schema.get("properties", {})):
                    raise SystemExit(f"MCP schema properties differ for {tool.name}")
                if set(mcp_schema.get("required", [])) != set(registry_schema.get("required", [])):
                    raise SystemExit(f"MCP required arguments differ for {tool.name}")

            tickets = await session.call_tool("get_open_tickets", {"customer_id": "C003"})
            policy = await session.call_tool("search_policy_docs", {"query": "refund policy", "top_k": 2})
            if tickets.isError or policy.isError:
                raise SystemExit("MCP tool call returned an error.")
            print(f"MCP initialize: PASS")
            print(f"MCP list_tools ({len(names)}): PASS")
            print("MCP registry schema parity: PASS")
            print("MCP get_open_tickets: PASS")
            print("MCP search_policy_docs: PASS")


if __name__ == "__main__":
    anyio.run(run_smoke_test)
