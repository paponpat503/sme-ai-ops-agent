from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Protocol

import anyio

from app.schemas.models import ToolCallResponse
from app.security.context import PrincipalContext
from app.tools.registry import call_registered_tool


class ToolTransport(Protocol):
    name: str
    def call(self, tool_name: str, arguments: dict[str, Any], principal: PrincipalContext) -> ToolCallResponse: ...


class LocalToolTransport:
    name = "local"

    def call(self, tool_name: str, arguments: dict[str, Any], principal: PrincipalContext) -> ToolCallResponse:
        result = call_registered_tool(tool_name, arguments, principal)
        return ToolCallResponse(
            tool_name=tool_name,
            result=result.result,
            error=result.error,
            error_code=result.error_code,
        )


class MCPToolTransport:
    name = "mcp"

    def call(self, tool_name: str, arguments: dict[str, Any], principal: PrincipalContext) -> ToolCallResponse:
        try:
            return anyio.run(self._call_async, tool_name, arguments, principal)
        except (ImportError, RuntimeError, OSError, ValueError) as exc:
            return ToolCallResponse(tool_name=tool_name, error=f"MCP transport failed: {exc}")

    async def _call_async(self, tool_name: str, arguments: dict[str, Any], principal: PrincipalContext) -> ToolCallResponse:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError("MCP SDK is not installed.") from exc

        root = Path(__file__).resolve().parents[2]
        from app.config import get_settings
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(root / "mcp" / "server.py")],
            cwd=str(root),
            env={
                **os.environ,
                "MCP_TENANT_ID": principal.tenant_id,
                "MCP_USER_ID": principal.user_id,
                "MCP_ROLES": ",".join(sorted(principal.roles)),
                "MCP_REQUEST_ID": principal.request_id,
            },
        )
        with anyio.fail_after(get_settings().request_timeout_seconds):
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    response = await session.call_tool(tool_name, arguments)
                    if response.isError:
                        message = " ".join(getattr(item, "text", str(item)) for item in response.content)
                        return ToolCallResponse(tool_name=tool_name, error=message, error_code="execution_error")
                    structured = getattr(response, "structuredContent", None)
                    if structured is not None:
                        if isinstance(structured, dict) and set(structured) == {"result"}:
                            structured = structured["result"]
                        return ToolCallResponse(tool_name=tool_name, result=structured)
                    text = "".join(getattr(item, "text", "") for item in response.content)
                    try:
                        result = json.loads(text)
                    except json.JSONDecodeError:
                        result = text
                    return ToolCallResponse(tool_name=tool_name, result=result)


def get_tool_transport(name: str) -> ToolTransport:
    return MCPToolTransport() if name == "mcp" else LocalToolTransport()


def tool_transport_is_ready(name: str) -> bool:
    if name == "local":
        return True
    try:
        from mcp import ClientSession  # noqa: F401
    except ImportError:
        return False
    return (Path(__file__).resolve().parents[2] / "mcp" / "server.py").is_file()
