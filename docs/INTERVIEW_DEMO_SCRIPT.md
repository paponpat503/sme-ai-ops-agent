# Interview Demo Script

## 30-Second Pitch

I built an SME operations agent that turns customer, support, billing, CRM, and policy data into evidence-backed next actions. It combines FastAPI, structured LLM output, validated tool planning, real MCP tool transport, tenant-aware data adapters, retrieval evaluation, deterministic fallback, and an operational dashboard. The point is reliable B2B automation, not an unconstrained chatbot.

## 2-Minute Technical Explanation

The API establishes a request and tenant context before orchestration begins. In tool-agent mode, a deterministic or LLM planner proposes a bounded `ToolPlan`. Pydantic rejects unknown fields and invalid arguments; policy checks reject unknown, unauthorized, duplicate, over-budget, or write-capable model calls. Approved calls run through the local registry or a real MCP stdio session. Results are synthesized into `AgentAnswer`, then checked against known customers and evidence. Provider or validation failures use the deterministic path, and the response records fallback reason, latency, tokens, and the tool trace.

Policy retrieval uses stable chunks, source/version metadata, score thresholds, and abstention. CRM access sits behind CSV and SQLAlchemy repository adapters, with tenant filtering at the storage boundary.

## 5-Minute Live Demo

1. Open `/demo` and point out run metadata, risk cards, tool trace, and registry controls.
2. Ask: `Which customers need follow-up today?` Show ranked actions, evidence IDs, and draft messages.
3. Run with `AGENT_MODE=tool_agent`. Explain plan, execution, observation, synthesis, per-call latency, planner, and transport.
4. In Tool Registry Demo, call `search_policy_docs` with `{"query":"enterprise refund approval","top_k":2}` and inspect citations.
5. Show `py -m scripts.run_mcp_smoke_test`, `py -m scripts.run_eval`, and `py -m scripts.run_retrieval_eval` passing. Explain that disabling the provider still returns a deterministic answer.

## Useful Agent Questions

- Which customers need follow-up today?
- Which enterprise accounts are risky?
- Which customers have both overdue payments and unresolved tickets?
- What is the enterprise refund policy?
- When should a customer be escalated to a manager?

## Explaining the Safety Features

The tool trace is an audit record: what was planned, why, what arguments were validated, what ran, how long it took, and whether it failed. The model never executes code directly.

Deterministic fallback protects the workflow when a provider is missing, times out, returns malformed output, or creates an unsafe plan. Fallback is visible rather than silently presented as model output.

MCP is the protocol boundary. The smoke test launches the server, negotiates a client session, discovers tools, and calls CRM and retrieval tools over stdio. The same registry contracts remain authoritative.

Evaluation covers output schema, expected and forbidden customers, actions, evidence, hallucination checks, plan policy, tenant isolation, retrieval relevance, abstention, API authentication, and protocol integration.

For B2B AI automation roles, this demonstrates orchestration, tool governance, grounding, multi-tenant architecture, resilience, observability, evaluation design, deployment, and the ability to translate business workflows into controlled AI systems.
