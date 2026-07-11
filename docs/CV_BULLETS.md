# CV Bullets

## Short

- Built and deployed a tenant-aware B2B AI operations agent using FastAPI, Pydantic, RAG, MCP, and deterministic fallback.
- Implemented strictly validated LLM tool plans with capability controls, auditable traces, and grounded structured outputs.
- Created automated agent, retrieval, security, MCP protocol, dashboard, and data-adapter evaluation gates.

## Detailed

- Designed an orchestration layer that converts CRM, ticket, billing, notes, and policy data into ranked, evidence-backed customer actions and professional follow-up drafts.
- Built a real MCP stdio client/server integration with tool discovery, typed invocation, controlled errors, and parity with the application tool registry.
- Added Pydantic tool schemas and execution policy that reject unknown fields, invalid dependencies, duplicate calls, unauthorized capabilities, excessive plans, and LLM-initiated write tools.
- Separated storage behind CSV and SQLAlchemy/PostgreSQL-ready repository adapters with tenant-keyed records and cross-tenant isolation tests.
- Established release gates for schema validity, hallucination prevention, retrieval Recall@5/MRR, negative-query abstention, API authentication, deterministic fallback, latency, and token metadata.

## Project Description

SME AI Ops Agent is a deployed B2B automation system for customer-success and operations workflows. It combines deterministic and LLM-ready orchestration, validated business-tool planning, real MCP transport, tenant-scoped CRM/data adapters, policy retrieval, structured Pydantic responses, grounding checks, operational telemetry, and deterministic fallback. A browser dashboard exposes customer risk, evidence, tool traces, latency, token usage, and validation status, while automated evaluations turn reliability and security requirements into repeatable release gates.
