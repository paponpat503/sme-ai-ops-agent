# MCP Server

This folder contains a minimal Model Context Protocol server for the SME AI Ops Agent.

MCP lets AI clients call local business tools instead of guessing business facts from the prompt. In this project, the server exposes the same CRM and RAG functions used by the FastAPI app and deterministic agent.

## Server

```text
mcp/server.py
```

The server uses the Python MCP SDK and stdio transport via `FastMCP`.

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Run the server:

```powershell
py mcp\server.py
```

## Exposed Tools

- `search_customers`
- `get_customer_profile`
- `get_open_tickets`
- `get_overdue_orders`
- `get_recent_notes`
- `search_policy_docs`
- `draft_followup_email`
- `create_crm_task_demo`

## Local Smoke Test

The smoke test calls the registry directly, so it works even if an MCP client is not configured yet:

```powershell
py -m scripts.run_mcp_smoke_test
```

## Client Configuration Later

For Claude Desktop, Claude Code, or another MCP-compatible client, point the client command to:

```powershell
py mcp\server.py
```

Use the repository root as the working directory so the server can import `app.*` modules and load local data/docs.
