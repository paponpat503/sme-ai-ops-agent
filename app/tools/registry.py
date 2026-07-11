from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.rag.runtime import rag_runtime
from app.tools.crm_tools import (
    create_crm_task,
    draft_followup_email,
    get_customer_profile,
    get_open_tickets,
    get_overdue_orders,
    get_recent_notes,
    search_customers,
)
from app.security.context import PrincipalContext, get_principal, reset_principal, set_principal


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchCustomersArgs(ToolArguments):
    query: str = Field(min_length=0, max_length=200)


class CustomerIdArgs(ToolArguments):
    customer_id: str = Field(pattern=r"^C\d{3,}$")


class OptionalCustomerIdArgs(ToolArguments):
    customer_id: str | None = Field(default=None, pattern=r"^C\d{3,}$")


class RecentNotesArgs(OptionalCustomerIdArgs):
    limit: int = Field(default=5, ge=1, le=100)


class PolicySearchArgs(ToolArguments):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class DraftEmailArgs(ToolArguments):
    customer_name: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=1000)
    action: str = Field(min_length=1, max_length=500)


class CreateTaskArgs(ToolArguments):
    customer_id: str = Field(pattern=r"^C\d{3,}$")
    task: str = Field(min_length=1, max_length=500)
    due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    owner: str = Field(default="sales", min_length=1, max_length=80)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=200)


class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResponse(BaseModel):
    tool_name: str
    result: Any = None
    error: str | None = None
    error_code: Literal["unknown_tool", "forbidden", "invalid_arguments", "execution_error"] | None = None


@dataclass(frozen=True)
class BusinessTool:
    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    callable: Callable[..., Any]
    argument_model: type[ToolArguments]
    capability: str
    read_only: bool = True
    safety_notes: str | None = None


def search_policy_docs(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    hits = rag_runtime.search(query=query, top_k=top_k, tenant_id=get_principal().tenant_id)
    return [hit.model_dump() for hit in hits]


def create_crm_task_demo(
    customer_id: str,
    task: str,
    due_date: str,
    owner: str = "sales",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    return create_crm_task(
        customer_id=customer_id,
        task=task,
        due_date=due_date,
        owner=owner,
        idempotency_key=idempotency_key,
    )


TOOL_REGISTRY: dict[str, BusinessTool] = {
    "search_customers": BusinessTool(
        name="search_customers",
        description="Search CRM customer records by name, industry, plan, owner, or other profile text.",
        parameters={
            "query": {"type": "string", "required": True, "description": "Search text."},
        },
        callable=search_customers,
        argument_model=SearchCustomersArgs,
        capability="crm:read",
        safety_notes="Read-only CRM lookup. Do not invent customers not returned by this tool.",
    ),
    "get_customer_profile": BusinessTool(
        name="get_customer_profile",
        description="Get one CRM customer profile by customer_id.",
        parameters={
            "customer_id": {"type": "string", "required": True, "description": "Customer ID, such as C001."},
        },
        callable=get_customer_profile,
        argument_model=CustomerIdArgs,
        capability="crm:read",
        safety_notes="Read-only CRM lookup. Unknown IDs return an error payload.",
    ),
    "get_open_tickets": BusinessTool(
        name="get_open_tickets",
        description="List open support tickets, optionally filtered by customer_id.",
        parameters={
            "customer_id": {"type": "string|null", "required": False, "description": "Optional customer ID."},
        },
        callable=get_open_tickets,
        argument_model=OptionalCustomerIdArgs,
        capability="crm:read",
        safety_notes="Read-only support data. Use ticket IDs as evidence.",
    ),
    "get_overdue_orders": BusinessTool(
        name="get_overdue_orders",
        description="List overdue orders, optionally filtered by customer_id.",
        parameters={
            "customer_id": {"type": "string|null", "required": False, "description": "Optional customer ID."},
        },
        callable=get_overdue_orders,
        argument_model=OptionalCustomerIdArgs,
        capability="billing:read",
        safety_notes="Read-only billing data. Use order IDs as evidence.",
    ),
    "get_recent_notes": BusinessTool(
        name="get_recent_notes",
        description="List recent CRM notes, optionally filtered by customer_id.",
        parameters={
            "customer_id": {"type": "string|null", "required": False, "description": "Optional customer ID."},
            "limit": {"type": "integer", "required": False, "description": "Maximum number of notes to return."},
        },
        callable=get_recent_notes,
        argument_model=RecentNotesArgs,
        capability="crm:read",
        safety_notes="Read-only CRM notes. Use notes as supporting evidence, not as invented facts.",
    ),
    "search_policy_docs": BusinessTool(
        name="search_policy_docs",
        description="Search company policy and onboarding documents through the local RAG index.",
        parameters={
            "query": {"type": "string", "required": True, "description": "Policy search query."},
            "top_k": {"type": "integer", "required": False, "description": "Number of chunks to return, 1-10."},
        },
        callable=search_policy_docs,
        argument_model=PolicySearchArgs,
        capability="policy:read",
        safety_notes="Read-only policy retrieval. Cite returned source/doc_id values.",
    ),
    "draft_followup_email": BusinessTool(
        name="draft_followup_email",
        description="Draft a concise customer follow-up email from a customer name, reason, and action.",
        parameters={
            "customer_name": {"type": "string", "required": True, "description": "Known customer name."},
            "reason": {"type": "string", "required": True, "description": "Evidence-backed reason for follow-up."},
            "action": {"type": "string", "required": True, "description": "Requested next action."},
        },
        callable=draft_followup_email,
        argument_model=DraftEmailArgs,
        capability="draft:write",
        safety_notes="Draft only. Do not send email automatically.",
    ),
    "create_crm_task_demo": BusinessTool(
        name="create_crm_task_demo",
        description="Create a demo CRM task payload. This does not write to a real CRM.",
        parameters={
            "customer_id": {"type": "string", "required": True, "description": "Customer ID."},
            "task": {"type": "string", "required": True, "description": "Task description."},
            "due_date": {"type": "string", "required": True, "description": "Due date string."},
            "owner": {"type": "string", "required": False, "description": "Task owner, default sales."},
            "idempotency_key": {"type": "string|null", "required": False, "description": "Stable retry key."},
        },
        callable=create_crm_task_demo,
        argument_model=CreateTaskArgs,
        capability="task:write",
        read_only=False,
        safety_notes="Demo write only. Returns a fake task creation payload.",
    ),
}


def list_registered_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "safety_notes": tool.safety_notes,
            "capability": tool.capability,
            "read_only": tool.read_only,
            "input_schema": tool.argument_model.model_json_schema(),
        }
        for tool in TOOL_REGISTRY.values()
    ]


def call_registered_tool(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    principal: PrincipalContext | None = None,
) -> ToolExecutionResponse:
    arguments = arguments or {}
    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        return ToolExecutionResponse(
            tool_name=tool_name,
            error=f"Unknown tool: {tool_name}",
            error_code="unknown_tool",
        )

    principal = principal or get_principal()
    if not principal.can(tool.capability):
        return ToolExecutionResponse(
            tool_name=tool_name,
            error=f"Forbidden: capability {tool.capability} is required.",
            error_code="forbidden",
        )

    try:
        bound_arguments = _validate_arguments(tool, arguments)
    except (TypeError, ValueError, ValidationError) as exc:
        return ToolExecutionResponse(tool_name=tool_name, error=str(exc), error_code="invalid_arguments")

    try:
        token = set_principal(principal)
        try:
            result = tool.callable(**bound_arguments)
        finally:
            reset_principal(token)
        return ToolExecutionResponse(tool_name=tool_name, result=_to_jsonable(result))
    except (TypeError, ValueError, PermissionError, RuntimeError, SQLAlchemyError) as exc:
        return ToolExecutionResponse(tool_name=tool_name, error=str(exc), error_code="execution_error")


def _validate_arguments(tool: BusinessTool, arguments: dict[str, Any]) -> dict[str, Any]:
    validated = tool.argument_model.model_validate(arguments).model_dump()
    signature = inspect.signature(tool.callable)
    try:
        bound = signature.bind(**validated)
    except TypeError as exc:
        raise ValueError(f"Invalid arguments for {tool.name}: {exc}") from exc
    bound.apply_defaults()
    return dict(bound.arguments)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value
