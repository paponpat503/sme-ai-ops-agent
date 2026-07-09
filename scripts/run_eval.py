from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from app.agents.llm_ops_agent import answer_with_agent, answer_with_agent_result
from app.llm.output_validation import validate_grounding
from app.schemas.models import AgentAnswer
from app.tools.crm_tools import load_customers
from app.tools.registry import TOOL_REGISTRY, call_registered_tool

EVAL_PATH = Path(__file__).resolve().parents[1] / "eval" / "eval_cases.json"
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

def run_eval() -> None:
    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    valid_customer_names = set(load_customers()["customer_name"].astype(str))
    total = 0
    passed = 0
    for case in cases:
        total += 1
        answer = answer_with_agent(case["question"])
        names = {a.customer_name for a in answer.actions}
        action_types = {a.recommended_action for a in answer.actions}
        checks = []
        checks.append(("valid_schema", _is_valid_schema(answer)))
        checks.append(("intent", answer.intent == case["expected_intent"]))
        for name in case.get("must_include_customers", []):
            checks.append((f"include:{name}", name in names))
        for name in case.get("must_not_include_customers", []):
            checks.append((f"exclude:{name}", name not in names))
        for action_type in case.get("required_action_types", []):
            checks.append((f"action:{action_type}", action_type in action_types))
        checks.append(("evidence_present", all(bool(a.evidence) for a in answer.actions)))
        checks.append(("grounded_evidence", _has_grounded_evidence(answer)))
        checks.append(("no_hallucinated_customers", names.issubset(valid_customer_names)))
        checks.append(("actionable_drafts", _has_required_drafts(answer)))
        case_pass = all(ok for _, ok in checks)
        passed += int(case_pass)
        print(f"\n{case['id']} :: {'PASS' if case_pass else 'FAIL'}")
        for label, ok in checks:
            print(f"  {'PASS' if ok else 'FAIL'} {label}")
    registry_pass = _run_tool_registry_eval()
    tool_agent_pass = _run_tool_agent_eval(valid_customer_names)
    print(f"\nOverall: {passed}/{total} agent cases passed")
    print(f"Tool registry: {'PASS' if registry_pass else 'FAIL'}")
    print(f"Tool agent: {'PASS' if tool_agent_pass else 'FAIL'}")


def _is_valid_schema(answer: AgentAnswer) -> bool:
    try:
        AgentAnswer.model_validate(answer.model_dump())
        return True
    except ValidationError:
        return False


def _has_grounded_evidence(answer: AgentAnswer) -> bool:
    try:
        validate_grounding(answer)
        return True
    except ValueError:
        return False


def _has_required_drafts(answer: AgentAnswer) -> bool:
    return all(
        action.recommended_action == "no_action" or bool(action.draft_message)
        for action in answer.actions
    )


def _run_tool_registry_eval() -> bool:
    checks = []
    registered = set(TOOL_REGISTRY)
    checks.append(("registry_expected_tools", EXPECTED_TOOLS.issubset(registered)))

    tickets = call_registered_tool("get_open_tickets", {"customer_id": "C003"})
    checks.append(("registry_get_open_tickets_no_error", tickets.error is None))
    checks.append(("registry_get_open_tickets_result", bool(tickets.result)))

    policy = call_registered_tool("search_policy_docs", {"query": "refund policy", "top_k": 2})
    checks.append(("registry_search_policy_docs_no_error", policy.error is None))
    checks.append(("registry_search_policy_docs_result", bool(policy.result)))

    print("\ntool_registry :: " + ("PASS" if all(ok for _, ok in checks) else "FAIL"))
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'} {label}")
    return all(ok for _, ok in checks)


def _run_tool_agent_eval(valid_customer_names: set[str]) -> bool:
    previous_mode = os.environ.get("AGENT_MODE")
    os.environ["AGENT_MODE"] = "tool_agent"
    try:
        result = answer_with_agent_result("Which customers need follow-up today?")
    finally:
        if previous_mode is None:
            os.environ.pop("AGENT_MODE", None)
        else:
            os.environ["AGENT_MODE"] = previous_mode

    trace = result.tool_trace
    names = {action.customer_name for action in result.answer.actions}
    tools_called = set(result.metadata.tools_called)
    checks = [
        ("tool_agent_trace_present", trace is not None),
        ("tool_agent_plan_not_empty", bool(trace and trace.plan)),
        ("tool_agent_required_tools", {"get_open_tickets", "get_overdue_orders"}.issubset(tools_called)),
        ("tool_agent_no_hallucinated_customers", names.issubset(valid_customer_names)),
        ("tool_agent_evidence_present", all(bool(action.evidence) for action in result.answer.actions)),
    ]

    print("\ntool_agent :: " + ("PASS" if all(ok for _, ok in checks) else "FAIL"))
    for label, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'} {label}")
    return all(ok for _, ok in checks)


if __name__ == "__main__":
    run_eval()
