from __future__ import annotations
from typing import List
from app.schemas.models import AgentAnswer, CustomerAction
from app.tools.crm_tools import load_customers, get_open_tickets, get_overdue_orders, get_recent_notes, draft_followup_email
from app.rag.runtime import rag_runtime

def answer_with_deterministic_agent(question: str) -> AgentAnswer:
    q = question.lower().strip()
    if "refund" in q or "policy" in q or "onboarding" in q:
        hits = rag_runtime.search(question, top_k=3)
        evidence = [f"{h.source}: {h.text[:220]}" for h in hits]
        return AgentAnswer(
            intent="knowledge_retrieval",
            summary="Retrieved relevant company knowledge. Use the RAG endpoint to inspect evidence snippets.",
            actions=[],
            missing_information=[] if evidence else ["No relevant policy documents found."],
            confidence="high" if evidence else "low",
        )
    if "follow" in q or "at risk" in q or "urgent" in q or "customer" in q or "enterprise" in q:
        return _customers_need_followup(question)
    return AgentAnswer(
        intent="general_question",
        summary="I can help with customer follow-up, open tickets, overdue payments, CRM notes, and company knowledge retrieval.",
        actions=[],
        missing_information=[],
        confidence="medium",
    )

def _customers_need_followup(question: str) -> AgentAnswer:
    customers = load_customers()
    open_tickets = get_open_tickets()
    overdue_orders = get_overdue_orders()
    q = question.lower()
    actions: List[CustomerAction] = []
    for _, c in customers.iterrows():
        customer_id = c["customer_id"]
        customer_name = c["customer_name"]
        if "enterprise" in q and str(c.get("plan", "")).lower() != "enterprise":
            continue
        customer_tickets = [t for t in open_tickets if t["customer_id"] == customer_id]
        customer_overdue = [o for o in overdue_orders if o["customer_id"] == customer_id]
        notes = get_recent_notes(customer_id, limit=2)
        if not customer_tickets and not customer_overdue:
            continue
        score = 30
        reasons = []
        evidence = []
        if customer_tickets:
            max_age = max(int(t["days_open"]) for t in customer_tickets)
            score += min(40, max_age * 5)
            reasons.append(f"{len(customer_tickets)} open support ticket(s), oldest open for {max_age} days")
            evidence.extend([f"Ticket {t['ticket_id']}: {t['issue']} ({t['days_open']} days open)" for t in customer_tickets])
        if customer_overdue:
            amount = sum(float(o["amount_usd"]) for o in customer_overdue)
            score += 25
            reasons.append(f"overdue payment of ${amount:,.0f}")
            evidence.extend([f"Order {o['order_id']}: overdue ${float(o['amount_usd']):,.0f}" for o in customer_overdue])
        if str(c.get("plan", "")).lower() == "enterprise":
            score += 10
            reasons.append("enterprise account")
        score = min(score, 100)
        if score >= 100:
            risk = "critical"
            recommended_action = "escalate_to_manager"
            action_text = "escalate this and schedule a support call"
        elif score >= 70:
            risk = "high"
            recommended_action = "schedule_support_call"
            action_text = "schedule a support call"
        elif score >= 50:
            risk = "medium"
            recommended_action = "send_followup_email"
            action_text = "send a follow-up email"
        else:
            risk = "low"
            recommended_action = "create_crm_task"
            action_text = "create a follow-up task"
        reason = "; ".join(reasons)
        if notes:
            evidence.extend([f"CRM note {n['date']}: {n['note']}" for n in notes])
        actions.append(CustomerAction(
            customer_id=customer_id,
            customer_name=customer_name,
            risk_level=risk,
            reason=reason,
            recommended_action=recommended_action,
            priority_score=score,
            draft_message=draft_followup_email(customer_name, reason, action_text),
            evidence=evidence[:5],
        ))
    actions = sorted(actions, key=lambda x: x.priority_score, reverse=True)
    return AgentAnswer(
        intent="customer_followup_prioritization",
        summary=f"Found {len(actions)} customer(s) that need follow-up, ranked by operational risk.",
        actions=actions,
        missing_information=[],
        confidence="high",
    )
