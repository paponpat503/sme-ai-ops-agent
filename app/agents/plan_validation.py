from __future__ import annotations

import json

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.models import ToolPlan
from app.security.context import PrincipalContext
from app.tools.registry import TOOL_REGISTRY


class ToolPlanError(ValueError):
    pass


def parse_tool_plan(raw: str) -> ToolPlan:
    """Parse executable plans strictly. Deliberate JSON repair is not permitted."""
    try:
        payload = json.loads(raw)
        return ToolPlan.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ToolPlanError(f"Invalid tool plan: {exc}") from exc


def validate_tool_plan(plan: ToolPlan, principal: PrincipalContext) -> ToolPlan:
    settings = get_settings()
    if not plan.calls:
        raise ToolPlanError("Tool plan must contain at least one call.")
    if len(plan.calls) > settings.max_tool_calls:
        raise ToolPlanError(f"Tool plan exceeds the {settings.max_tool_calls}-call budget.")

    seen: set[str] = set()
    for index, call in enumerate(plan.calls):
        tool = TOOL_REGISTRY.get(call.tool_name)
        if tool is None:
            raise ToolPlanError(f"Unknown tool in plan: {call.tool_name}")
        if not tool.read_only:
            raise ToolPlanError(f"LLM plans may not invoke write tool: {call.tool_name}")
        if not principal.can(tool.capability):
            raise ToolPlanError(f"Forbidden tool in plan: {call.tool_name}")
        try:
            tool.argument_model.model_validate(call.arguments)
        except ValidationError as exc:
            raise ToolPlanError(f"Invalid arguments for {call.tool_name}: {exc}") from exc
        if any(dependency < 0 or dependency >= index for dependency in call.depends_on):
            raise ToolPlanError(f"Invalid dependency for plan call {index}.")
        fingerprint = f"{call.tool_name}:{json.dumps(call.arguments, sort_keys=True)}"
        if fingerprint in seen:
            raise ToolPlanError(f"Duplicate tool call: {call.tool_name}")
        seen.add(fingerprint)
    return plan
