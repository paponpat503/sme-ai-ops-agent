from __future__ import annotations

from app.schemas.models import ToolCallPlan


def plan_tool_calls(question: str) -> list[ToolCallPlan]:
    q = question.lower().strip()
    if _is_policy_question(q):
        return [
            ToolCallPlan(
                tool_name="search_policy_docs",
                arguments={"query": question, "top_k": 3},
                reason="Retrieve relevant company policy chunks before answering.",
            )
        ]

    if _is_customer_risk_question(q):
        customer_query = "enterprise" if "enterprise" in q else ""
        return [
            ToolCallPlan(
                tool_name="search_customers",
                arguments={"query": customer_query},
                reason="Identify the customer set in scope for the risk question.",
            ),
            ToolCallPlan(
                tool_name="get_open_tickets",
                arguments={},
                reason="Open support tickets are primary operational risk evidence.",
            ),
            ToolCallPlan(
                tool_name="get_overdue_orders",
                arguments={},
                reason="Overdue orders show commercial and billing risk.",
            ),
            ToolCallPlan(
                tool_name="get_recent_notes",
                arguments={"limit": 20},
                reason="CRM notes provide recent customer context and follow-up evidence.",
            ),
        ]

    return [
        ToolCallPlan(
            tool_name="search_policy_docs",
            arguments={"query": question, "top_k": 3},
            reason="Try knowledge retrieval for a general business question.",
        )
    ]


def _is_policy_question(q: str) -> bool:
    return any(term in q for term in ("refund", "policy", "onboarding"))


def _is_customer_risk_question(q: str) -> bool:
    terms = (
        "follow",
        "at risk",
        "risky",
        "urgent",
        "customer",
        "enterprise",
        "overdue",
        "open ticket",
        "open tickets",
    )
    return any(term in q for term in terms)
