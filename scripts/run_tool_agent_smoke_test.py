from __future__ import annotations

import os

from rich import print_json

from app.agents.llm_ops_agent import answer_with_agent_result
from app.schemas.models import AgentAnswer


QUESTION = "Which customers need follow-up today?"


def run_smoke_test() -> None:
    previous_mode = os.environ.get("AGENT_MODE")
    os.environ["AGENT_MODE"] = "tool_agent"
    try:
        result = answer_with_agent_result(QUESTION)
    finally:
        if previous_mode is None:
            os.environ.pop("AGENT_MODE", None)
        else:
            os.environ["AGENT_MODE"] = previous_mode

    tool_trace = result.tool_trace
    tools_called = result.metadata.tools_called
    AgentAnswer.model_validate(result.answer.model_dump())
    _assert(tool_trace is not None, "Expected tool trace.")
    _assert(bool(tool_trace.results), "Expected at least one tool call result.")
    _assert(
        "get_open_tickets" in tools_called or "get_overdue_orders" in tools_called,
        "Expected ticket or overdue-order tool call.",
    )
    _assert(any(action.evidence for action in result.answer.actions), "Expected customer action evidence.")

    print("metadata:")
    print_json(data=result.metadata.model_dump())
    print("answer:")
    print_json(data=result.answer.model_dump())
    print("tool_trace:")
    print_json(data=tool_trace.model_dump())
    print("tool_agent_smoke_test: PASS")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    run_smoke_test()
