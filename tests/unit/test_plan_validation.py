import json

import pytest

from app.agents.plan_validation import ToolPlanError, parse_tool_plan, validate_tool_plan
from app.schemas.models import ToolCallPlan, ToolPlan
from app.security.context import PrincipalContext


VIEWER = PrincipalContext("demo", "viewer", frozenset({"viewer"}), "test")


def test_valid_read_plan():
    plan = ToolPlan(calls=[ToolCallPlan(tool_name="get_open_tickets", arguments={}, reason="Inspect tickets")])
    assert validate_tool_plan(plan, VIEWER) == plan


@pytest.mark.parametrize(
    "call",
    [
        ToolCallPlan(tool_name="unknown", arguments={}, reason="bad"),
        ToolCallPlan(tool_name="get_open_tickets", arguments={"extra": True}, reason="bad"),
        ToolCallPlan(tool_name="create_crm_task_demo", arguments={"customer_id":"C001","task":"x","due_date":"2026-08-01"}, reason="bad"),
    ],
)
def test_rejects_unsafe_or_invalid_calls(call):
    with pytest.raises(ToolPlanError):
        validate_tool_plan(ToolPlan(calls=[call]), VIEWER)


def test_strict_parser_does_not_repair_json():
    with pytest.raises(ToolPlanError):
        parse_tool_plan('{"calls": [],}')


def test_rejects_duplicate_calls():
    call = ToolCallPlan(tool_name="get_open_tickets", arguments={}, reason="Inspect")
    with pytest.raises(ToolPlanError):
        validate_tool_plan(ToolPlan(calls=[call, call]), VIEWER)
