# LinkedIn Post

## Short Post

I built and deployed an SME AI Ops Agent for evidence-backed B2B customer operations. It combines FastAPI, validated LLM tool planning, real MCP tool calls, RAG, tenant-aware data adapters, structured outputs, deterministic fallback, and automated evaluations. The focus was making AI automation observable and controllable, not building another chat interface.

GitHub: https://github.com/YOUR-USERNAME/sme_ai_ops_agent

Live demo: https://YOUR-RENDER-LINK.onrender.com/demo

## Longer Post

I have been building an SME AI Ops Agent to explore what production-minded B2B AI automation looks like beyond prompting.

The agent inspects synthetic CRM, support, billing, notes, and policy data, then returns ranked customer actions with explicit evidence. An LLM can propose tool plans, but Pydantic schemas and application policy control what may execute. Unknown tools, invalid arguments, duplicate calls, excessive plans, unauthorized capabilities, and model-initiated writes are rejected. The same tools can run locally or through a real MCP stdio client/server session.

The system also includes tenant-scoped CSV and PostgreSQL-ready adapters, retrieval relevance and abstention metrics, request IDs, latency and token metadata, grounding checks, deterministic fallback, CI, and a dashboard that makes the execution trace visible.

This project helped me connect prompt engineering, agent orchestration, software boundaries, evaluation, and operational reliability into one deployable workflow.

GitHub: https://github.com/YOUR-USERNAME/sme_ai_ops_agent

Live demo: https://YOUR-RENDER-LINK.onrender.com/demo

## Screenshot Carousel

1. Dashboard overview with the question, metadata, and customer risk cards.
2. Evidence-backed customer action with ticket, order, and CRM note IDs.
3. Tool trace showing planner, transport, validated calls, and latency.
4. Tool registry policy retrieval with source citations.
5. README architecture diagram.
6. Terminal with agent, retrieval, MCP, and security tests passing.

## Hashtags

#ArtificialIntelligence #LLM #AIAgents #MCP #RAG #FastAPI #Python #B2BAutomation #PromptEngineering #MLOps
