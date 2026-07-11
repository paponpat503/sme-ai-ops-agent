from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import os
import time
from typing import Any

from app.agents.ops_agent import answer_with_deterministic_agent
from app.agents.tool_planner import plan_tool_calls
from app.agents.llm_tool_planner import generate_tool_plan
from app.agents.plan_validation import ToolPlanError
from app.config import get_settings
from app.llm.providers import get_llm_provider
from app.llm.output_validation import AgentOutputError, validate_grounding
from app.schemas.models import AgentAnswer, CustomerAction, ToolAgentTrace, ToolCallResult
from app.tools.crm_tools import draft_followup_email
from app.security.context import get_principal
from app.tools.transport import get_tool_transport
from app.telemetry import get_tracer


@dataclass(frozen=True)
class ToolAgentResult:
    answer: AgentAnswer
    trace: ToolAgentTrace
    fallback_used: bool
    error: str | None = None


def answer_with_tool_agent(question: str) -> ToolAgentResult:
    principal = get_principal()
    planner = "deterministic"
    planning_error: str | None = None
    if os.getenv("TOOL_PLANNER", "deterministic").strip().lower() == "llm":
        try:
            plan = generate_tool_plan(question, get_llm_provider(), principal).calls
            planner = "llm"
        except ToolPlanError as exc:
            plan = plan_tool_calls(question)
            planning_error = str(exc)
    else:
        plan = plan_tool_calls(question)

    transport = get_tool_transport(get_settings().tool_transport)
    results = [_execute_plan_item(item, transport, principal) for item in plan]
    trace = ToolAgentTrace(plan=plan, results=results, planner=planner, transport=transport.name)
    try:
        answer = _synthesize_answer(question, trace)
        validate_grounding(answer)
        return ToolAgentResult(
            answer=answer,
            trace=trace,
            fallback_used=planning_error is not None,
            error=planning_error,
        )
    except (AgentOutputError, ValueError, TypeError, KeyError) as exc:
        return ToolAgentResult(
            answer=answer_with_deterministic_agent(question),
            trace=trace,
            fallback_used=True,
            error=str(exc),
        )


def _execute_plan_item(plan_item: Any, transport: Any, principal: Any) -> ToolCallResult:
    started = time.perf_counter()
    with get_tracer().start_as_current_span("tool.execute") as span:
        span.set_attribute("tool.name", plan_item.tool_name)
        span.set_attribute("tool.transport", transport.name)
        span.set_attribute("tenant.id", principal.tenant_id)
        response = transport.call(plan_item.tool_name, plan_item.arguments, principal)
        span.set_attribute("tool.error", bool(response.error))
    return ToolCallResult(
        tool_name=plan_item.tool_name,
        arguments=plan_item.arguments,
        result=response.result,
        error=response.error,
        error_code=response.error_code,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        validation_status="execution_error" if response.error else "valid",
    )


def _synthesize_answer(question: str, trace: ToolAgentTrace) -> AgentAnswer:
    q = question.lower()
    result_by_tool = {result.tool_name: result for result in trace.results}

    if "search_policy_docs" in result_by_tool and not _is_customer_risk_question(q):
        return _synthesize_policy_answer(result_by_tool["search_policy_docs"])

    return _synthesize_customer_risk_answer(question, result_by_tool)


def _synthesize_policy_answer(policy_result: ToolCallResult) -> AgentAnswer:
    hits = policy_result.result or []
    if policy_result.error:
        return AgentAnswer(
            intent="knowledge_retrieval",
            summary="Policy retrieval failed, so no grounded policy answer was produced.",
            actions=[],
            missing_information=[policy_result.error],
            confidence="low",
        )
    return AgentAnswer(
        intent="knowledge_retrieval",
        summary="Retrieved relevant company knowledge from policy documents.",
        actions=[],
        missing_information=[] if hits else ["No relevant policy documents found."],
        confidence="high" if hits else "low",
    )


def _synthesize_customer_risk_answer(question: str, result_by_tool: dict[str, ToolCallResult]) -> AgentAnswer:
    customers = _require_list(result_by_tool, "search_customers")
    open_tickets = _require_list(result_by_tool, "get_open_tickets")
    overdue_orders = _require_list(result_by_tool, "get_overdue_orders")
    recent_notes = _require_list(result_by_tool, "get_recent_notes")

    q = question.lower()
    notes_by_customer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for note in recent_notes:
        notes_by_customer[str(note.get("customer_id"))].append(note)

    actions: list[CustomerAction] = []
    for customer in customers:
        customer_id = str(customer["customer_id"])
        customer_name = str(customer["customer_name"])
        if "enterprise" in q and str(customer.get("plan", "")).lower() != "enterprise":
            continue

        customer_tickets = [ticket for ticket in open_tickets if ticket.get("customer_id") == customer_id]
        customer_overdue = [order for order in overdue_orders if order.get("customer_id") == customer_id]
        if "overdue" in q and "ticket" in q and (not customer_tickets or not customer_overdue):
            continue
        if not customer_tickets and not customer_overdue:
            continue

        action = _build_customer_action(customer, customer_tickets, customer_overdue, notes_by_customer[customer_id])
        actions.append(action)

    actions = sorted(actions, key=lambda item: item.priority_score, reverse=True)
    return AgentAnswer(
        intent="customer_followup_prioritization",
        summary=f"Tool agent found {len(actions)} customer(s) that need follow-up, ranked by operational risk.",
        actions=actions,
        missing_information=[],
        confidence="high" if actions else "medium",
    )


def _build_customer_action(
    customer: dict[str, Any],
    tickets: list[dict[str, Any]],
    overdue_orders: list[dict[str, Any]],
    notes: list[dict[str, Any]],
) -> CustomerAction:
    customer_id = str(customer["customer_id"])
    customer_name = str(customer["customer_name"])
    score = 30
    reasons: list[str] = []
    evidence: list[str] = []

    if tickets:
        max_age = max(int(ticket["days_open"]) for ticket in tickets)
        score += min(40, max_age * 5)
        reasons.append(f"{len(tickets)} open support ticket(s), oldest open for {max_age} days")
        evidence.extend(
            f"Ticket {ticket['ticket_id']}: {ticket['issue']} ({ticket['days_open']} days open)"
            for ticket in tickets
        )

    if overdue_orders:
        amount = sum(float(order["amount_usd"]) for order in overdue_orders)
        score += 25
        reasons.append(f"overdue payment of ${amount:,.0f}")
        evidence.extend(
            f"Order {order['order_id']}: overdue ${float(order['amount_usd']):,.0f}"
            for order in overdue_orders
        )

    if str(customer.get("plan", "")).lower() == "enterprise":
        score += 10
        reasons.append("enterprise account")

    score = min(score, 100)
    risk, recommended_action, action_text = _classify_action(score)
    sorted_notes = sorted(notes, key=lambda item: str(item.get("date", "")), reverse=True)
    evidence.extend(
        f"CRM note {note['date']}: {note['note']}"
        for note in sorted_notes[:2]
    )
    reason = "; ".join(reasons)

    return CustomerAction(
        customer_id=customer_id,
        customer_name=customer_name,
        risk_level=risk,
        reason=reason,
        recommended_action=recommended_action,
        priority_score=score,
        draft_message=draft_followup_email(customer_name, reason, action_text),
        evidence=evidence[:5],
    )


def _classify_action(score: int) -> tuple[str, str, str]:
    if score >= 100:
        return "critical", "escalate_to_manager", "escalate this and schedule a support call"
    if score >= 70:
        return "high", "schedule_support_call", "schedule a support call"
    if score >= 50:
        return "medium", "send_followup_email", "send a follow-up email"
    return "low", "create_crm_task", "create a follow-up task"


def _require_list(result_by_tool: dict[str, ToolCallResult], tool_name: str) -> list[dict[str, Any]]:
    result = result_by_tool.get(tool_name)
    if result is None:
        raise ValueError(f"Missing tool result: {tool_name}")
    if result.error:
        raise ValueError(f"{tool_name} failed: {result.error}")
    if not isinstance(result.result, list):
        raise TypeError(f"{tool_name} did not return a list")
    return result.result


def _is_customer_risk_question(q: str) -> bool:
    return any(
        term in q
        for term in ("follow", "at risk", "risky", "urgent", "customer", "enterprise", "overdue", "ticket")
    )
