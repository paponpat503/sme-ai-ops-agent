# SME AI Ops Agent

![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-portfolio_demo-purple)

SME AI Ops Agent is a B2B AI automation prototype demonstrating RAG, tool calling, structured outputs, MCP, validation, deterministic fallback, and evaluation.

## Live Demo

- Dashboard: https://YOUR-RENDER-LINK.onrender.com/demo
- API documentation: https://YOUR-RENDER-LINK.onrender.com/docs

The public demo uses synthetic business data and remains usable without an LLM key through deterministic fallback.

## Production and Interview Assets

- [Production architecture](docs/PRODUCTION_ARCHITECTURE.md)
- [Production runbook](docs/PRODUCTION_RUNBOOK.md)
- [Interview demo script](docs/INTERVIEW_DEMO_SCRIPT.md)
- [CV bullets](docs/CV_BULLETS.md)
- [LinkedIn post](docs/LINKEDIN_POST.md)
- [Screenshot checklist](docs/SCREENSHOT_CHECKLIST.md)

It is designed as a portfolio-grade project for roles like **AI Prompt Engineer**, **LLM Automation Builder**, and **AI Product Engineer**.

The goal is not to build another chatbot. The goal is to build an assistant that can:

1. Retrieve company knowledge with RAG.
2. Inspect structured business data.
3. Select tools.
4. Return validated JSON.
5. Draft customer-facing actions.
6. Evaluate reliability with test cases.

This is the exact kind of system a CRM / ERP / workflow SaaS company would care about.

---

## Why this is not just a chatbot

This project does more than send a prompt to a model and display text:

- **Tools:** Business functions expose CRM records, support tickets, overdue orders, notes, policy search, draft generation, and demo task creation.
- **Evidence:** Customer recommendations cite tickets, orders, CRM notes, or retrieved policy chunks.
- **JSON schemas:** Agent responses are shaped by Pydantic models such as `AgentAnswer`, `CustomerAction`, and tool-trace schemas.
- **Validation:** LLM output is parsed, repaired once if needed, validated, and checked for grounded customer names and evidence.
- **Fallback:** Deterministic logic protects reliability when an LLM is unavailable, invalid, or unsafe.
- **Evaluation:** Scripts verify intent, required customers, action types, evidence, hallucination checks, tool registry behavior, and tool-agent traces.
- **MCP:** The same business tools can be exposed to MCP-compatible AI clients so they call real tools instead of inventing business facts.

---

## Project structure

```text
sme_ai_ops_agent/
  app/
    agents/          deterministic, LLM, and tool-agent orchestration
    llm/             provider abstraction and OpenAI adapter
    rag/             lightweight TF-IDF document retrieval
    schemas/         Pydantic request, response, and trace models
    static/          browser demo dashboard
    tools/           CRM tools and business-tool registry
    main.py          FastAPI app and routes
  data/              demo CRM, ticket, order, and note CSVs
  docs/              policy and onboarding knowledge base
  eval/              evaluation cases
  mcp/               MCP stdio server used by the real client integration
  prompts/           structured-output prompt templates
  scripts/           demos, evals, and smoke tests
```

---

## Architecture diagram

```mermaid
flowchart TD
    User[User or AI client] --> API[FastAPI app]
    API --> Agent[/agent/ask]
    API --> ToolAPI[/tools/call and /tools/list]
    API --> Demo[/demo dashboard]

    Agent --> Mode{AGENT_MODE}
    Mode --> Deterministic[Deterministic fallback agent]
    Mode --> LLM[LLM provider abstraction]
    Mode --> ToolAgent[Tool-planning agent]

    LLM --> OpenAI[OpenAI provider]
    LLM --> Validation[Pydantic validation and grounding checks]
    ToolAgent --> Planner[Tool planner]
    Planner --> Registry[Business tool registry]
    ToolAPI --> Registry
    Registry --> CRM[CSV CRM data]
    Registry --> RAG[RAG policy search]
    RAG --> Docs[docs/ knowledge base]

    Validation --> Answer[Validated AgentAnswer]
    Deterministic --> Answer
    ToolAgent --> Answer
    Answer --> Demo
```

---

## Architecture overview

```text
FastAPI app
  /agent/ask
    -> app.agents.llm_ops_agent.answer_with_agent_result
       -> AGENT_MODE selects deterministic, llm, auto, or tool_agent
       -> build structured-output prompt
       -> selected LLM provider in AGENT_MODE=llm or auto
       -> or deterministic tool planning in AGENT_MODE=tool_agent
       -> parse and validate AgentAnswer JSON
       -> grounding checks
       -> deterministic fallback on missing provider or unsafe output
       -> response wrapper with answer + provider/fallback metadata + optional tool trace

  /tools/call
    -> app.tools.registry.call_registered_tool
       -> validated tool lookup
       -> JSON-serializable CRM/RAG tool result or clean error

  /demo
    -> browser dashboard for agent runs, metadata, tools, and architecture

  /rag/search
    -> app.rag.simple_rag.SimpleRagIndex
       -> TF-IDF retrieval over docs/

Deterministic baseline
  app.agents.ops_agent.answer_with_deterministic_agent
    -> CRM tools
    -> customer risk scoring
    -> grounded ticket/order/CRM-note evidence
```

Key files:

- `app/main.py` - FastAPI routes.
- `app/agents/ops_agent.py` - deterministic baseline and safety fallback.
- `app/agents/llm_ops_agent.py` - LLM orchestration, prompt construction, and fallback routing.
- `app/agents/tool_planner.py` - deterministic planner that chooses business tools for a question.
- `app/agents/tool_agent.py` - executes planned tools and synthesizes a grounded `AgentAnswer`.
- `app/llm/providers.py` - provider interface, OpenAI adapter, and future Anthropic / Gemini adapter placeholders.
- `app/llm/output_validation.py` - JSON parsing, one-step repair, schema validation, and grounding checks.
- `app/tools/crm_tools.py` - structured CRM-style tools.
- `app/tools/registry.py` - business-tool registry shared by FastAPI, eval, smoke tests, and MCP.
- `app/rag/simple_rag.py` - lightweight document retrieval.
- `app/schemas/models.py` - Pydantic schemas.
- `app/static/demo.html`, `app/static/styles.css`, `app/static/demo.js` - browser dashboard.
- `mcp/server.py` - local MCP stdio server exposing CRM/RAG tools.
- `prompts/structured_output_prompt.md` - strict JSON prompt for `AgentAnswer`.
- `eval/eval_cases.json` and `scripts/run_eval.py` - reliability checks.

---

## What this demonstrates

- Prompt engineering
- Tool calling architecture
- Structured JSON output
- RAG / retrieval
- Customer support and CRM automation
- Evaluation harness
- Backend API design with FastAPI
- LLM fallback / deterministic fallback design
- Agentic tool planning
- B2B workflow thinking

---

## Deterministic fallback

The deterministic agent is the baseline and safety fallback. It remains intact in `app/agents/ops_agent.py`.

Fallback is used when:

- `AGENT_MODE=deterministic` is set, which always uses the deterministic agent.
- `AGENT_MODE=tool_agent` fails during planning, execution, synthesis, or validation.
- The selected provider does not have an API key.
- The provider adapter is not implemented yet.
- The OpenAI request fails or returns an empty message.
- The model returns invalid JSON.
- One local repair attempt fails.
- The parsed answer fails `AgentAnswer` validation.
- The answer includes unknown customers, missing evidence, unsupported evidence, or missing draft messages for actionable recommendations.

This keeps the project runnable without API keys while still producing grounded CRM workflow recommendations.

---

## LLM provider abstraction

`app/llm/providers.py` defines a small provider interface:

- `is_configured()` checks local configuration.
- `generate(prompt)` returns an `LLMResult`.

Prepared provider names:

- `openai` via `OPENAI_API_KEY`
- `anthropic` via `ANTHROPIC_API_KEY`
- `gemini` via `GEMINI_API_KEY`

OpenAI is implemented first using the Chat Completions API with low temperature and JSON response formatting. Anthropic and Gemini remain adapter placeholders behind the same interface.

Agent modes:

- `AGENT_MODE=deterministic` - always use the deterministic agent.
- `AGENT_MODE=llm` - try the configured LLM provider, then fall back if unavailable or invalid.
- `AGENT_MODE=auto` - use LLM when a provider key exists, otherwise use deterministic mode.
- `AGENT_MODE=tool_agent` - plan business-tool calls, execute them through the registry, synthesize a grounded answer, then validate it.

OpenAI configuration:

```powershell
$env:LLM_PROVIDER = "openai"
$env:AGENT_MODE = "llm"
$env:OPENAI_API_KEY = "..."
$env:OPENAI_MODEL = "gpt-4o-mini"
```

Deterministic mode:

```powershell
$env:AGENT_MODE = "deterministic"
py -m scripts.run_demo
```

LLM mode:

```powershell
$env:LLM_PROVIDER = "openai"
$env:AGENT_MODE = "llm"
$env:OPENAI_API_KEY = "..."
py -m scripts.run_llm_smoke_test
```

Auto mode:

```powershell
$env:AGENT_MODE = "auto"
py -m scripts.run_demo
```

Tool-agent mode:

```powershell
$env:AGENT_MODE = "tool_agent"
py -m scripts.run_tool_agent_smoke_test
```

---

## Agentic tool planning

Agentic tool planning means the agent does not answer only from prompt text. It first creates a plan of business tools to call, executes those tools through the registry, observes the returned data, and then synthesizes a structured answer from those observations.

For customer-risk questions, the deterministic planner calls:

- `search_customers`
- `get_open_tickets`
- `get_overdue_orders`
- `get_recent_notes`

For policy questions, it calls:

- `search_policy_docs`

This differs from normal chatbot prompting because customer names, ticket status, overdue payments, and policy facts come from callable business systems rather than model memory. In a real B2B automation or CRM workflow, this pattern maps to assistants that inspect accounts, retrieve support and billing context, recommend next actions, and preserve an auditable trace of what data was used.

`/agent/ask` still returns:

```json
{
  "answer": {},
  "metadata": {},
  "tool_trace": null
}
```

When `AGENT_MODE=tool_agent`, `tool_trace` contains the planned tool calls and execution results.

Smoke test:

```powershell
py -m scripts.run_tool_agent_smoke_test
```

---

## Structured output and grounding

The structured prompt in `prompts/structured_output_prompt.md` forces future LLMs to return JSON matching the existing `AgentAnswer` schema.

Important rules:

- Return JSON only.
- Do not invent customers.
- Use only customers present in structured records.
- Every customer action must cite tickets, orders, CRM notes, or retrieved policy chunks.
- Put unavailable evidence in `missing_information`.
- Include `draft_message` for actionable recommendations.

---

## Business tool registry and MCP

The business-tool registry lives in `app/tools/registry.py`. It exposes the CRM and RAG tools with names, descriptions, parameter metadata, callables, and safety notes.

Registered tools:

- `search_customers`
- `get_customer_profile`
- `get_open_tickets`
- `get_overdue_orders`
- `get_recent_notes`
- `search_policy_docs`
- `draft_followup_email`
- `create_crm_task_demo`

MCP means Model Context Protocol. In this project, MCP allows AI clients such as Claude Desktop or Claude Code to call local business tools instead of hallucinating customer names, ticket status, payment state, or policy facts.

The local MCP server lives at:

```text
mcp/server.py
```

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Run the MCP stdio server:

```powershell
py mcp\server.py
```

For Claude Desktop, Claude Code, or another MCP client, configure the command as `py` with arguments `mcp\server.py`, and use this repository as the working directory.

Test a real MCP client/server stdio session:

```powershell
py -m scripts.run_mcp_smoke_test
```

---

## Browser demo dashboard

The project includes a self-contained browser dashboard served by FastAPI. It has no frontend build step and no JavaScript framework.

Run the app:

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

The dashboard shows:

- agent question input and structured customer risk cards
- run metadata such as `provider_used`, `fallback_used`, and `validation_status`
- tool-agent trace when `AGENT_MODE=tool_agent`
- a tool registry demo for calling CRM/RAG tools
- a short architecture summary for interviews and portfolio screenshots

Dashboard smoke test:

```powershell
py -m scripts.run_dashboard_smoke_test
```

---

## Deployment readiness

The project is ready for a simple public demo deployment on services such as Render, Railway, or Fly.io.

Dependency file:

```text
requirements.txt
```

Dependency check:

```powershell
py -m pip install -r requirements.txt
py -m pip check
```

Python runtime:

```text
runtime.txt
```

Process file:

```text
Procfile
```

Recommended production start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render setup:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `AGENT_MODE=auto` for deterministic fallback without requiring an API key.
  - `TOOL_PLANNER=deterministic` and `TOOL_TRANSPORT=local` for the public demo.
  - `APP_ENV=production` plus `APP_API_KEY` or a typed `APP_API_KEYS_JSON` identity map for protected APIs.
  - `DATABASE_URL` and `RETRIEVER_MODE=hybrid` for tenant-scoped PostgreSQL/pgvector retrieval.
  - `OTEL_EXPORTER_OTLP_ENDPOINT` only when exporting traces to an approved collector.
  - `TRUST_PROXY_HEADERS=true` only behind a proxy that replaces inbound forwarding headers.
  - `LLM_PROVIDER=openai` if enabling OpenAI later.
  - `OPENAI_API_KEY` only in the deployment provider's secret manager, never committed.

Public demo notes:

- The dashboard is available at `/demo`.
- The default behavior works without secrets because deterministic fallback is enabled.
- Live LLM mode is optional and should be enabled only with environment-managed secrets.
- `RUN_LIVE_LLM_EVAL=1` is required before any live quality/cost evaluation can execute.

---

## Quick start

```bash
cd sme_ai_ops_agent
py -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/demo
```

Try:

```bash
py -m scripts.run_demo
py -m scripts.run_eval
py -m scripts.run_llm_smoke_test
py -m scripts.run_mcp_smoke_test
py -m scripts.run_dashboard_smoke_test
py -m scripts.run_tool_agent_smoke_test
```

---

## Demo screenshots

Add screenshots under a future `docs/screenshots/` folder or attach them directly to your GitHub README.

Screenshot checklist:

- Dashboard overview
- Customer risk cards
- Tool trace
- Tool registry call
- Evaluation output

Suggested filenames:

```text
docs/screenshots/dashboard-overview.png
docs/screenshots/customer-risk-cards.png
docs/screenshots/tool-trace.png
docs/screenshots/tool-registry-call.png
docs/screenshots/evaluation-output.png
```

---

## Main endpoints

### Health

```http
GET /health
```

### Ask the SME AI Ops Agent

```http
POST /agent/ask
```

Example body:

```json
{
  "question": "Which customers need follow-up today?"
}
```

Example response shape:

```json
{
  "answer": {
    "intent": "customer_followup_prioritization",
    "summary": "...",
    "actions": [],
    "missing_information": [],
    "confidence": "high"
  },
  "metadata": {
    "agent_mode": "auto",
    "provider_used": "deterministic",
    "fallback_used": false,
    "validation_status": "not_attempted",
    "error": null,
    "tool_agent_used": false,
    "tool_calls_count": 0,
    "tools_called": []
  },
  "tool_trace": null
}
```

### Search knowledge base

```http
POST /rag/search
```

Example body:

```json
{
  "query": "refund policy for annual plan",
  "top_k": 3
}
```

### List registered business tools

```http
GET /tools/list
```

### Call a registered business tool

```http
POST /tools/call
```

Example body:

```json
{
  "tool_name": "get_open_tickets",
  "arguments": {
    "customer_id": "C003"
  }
}
```

Example response:

```json
{
  "tool_name": "get_open_tickets",
  "result": [],
  "error": null
}
```

---

## Portfolio framing

Use this project in your CV as:

> Built an SME AI operations assistant that combines RAG, structured JSON outputs, tool-calling architecture, CRM data inspection, customer-risk detection, and workflow recommendations. Designed evaluation tests for schema validity, groundedness, retrieval hit rate, and action quality.

## Portfolio positioning

This repository is positioned for AI Prompt Engineer, LLM Automation Builder, and AI Product Engineer applications. It demonstrates the work needed for reliable B2B AI systems:

- converting messy business context into structured workflow outputs
- calling tools instead of relying on model memory
- grounding recommendations in evidence
- validating JSON outputs before use
- exposing business tools to both APIs and MCP clients
- keeping deterministic fallback and evals as safety rails
- presenting the workflow in a browser demo suitable for LinkedIn and GitHub

## Demo talking points

- The dashboard is backed by real FastAPI endpoints, not static mock data.
- The agent output is structured as `AgentAnswer` and validated before display.
- Every customer recommendation includes evidence from tickets, orders, CRM notes, or policy retrieval.
- LLM usage is optional: deterministic fallback keeps the workflow reliable when no key is configured.
- Tool-agent mode shows the planning and execution trace behind a recommendation.
- The same business tools are exposed through FastAPI, eval scripts, and a real MCP stdio client/server session.
- The eval harness checks customer inclusion/exclusion, action types, evidence, drafts, and hallucinated names.

## LinkedIn screenshot ideas

- Full dashboard view with the three customer risk cards after running the default question.
- Close-up of run metadata showing deterministic fallback and validation status.
- Tool Trace panel showing planned calls to `get_open_tickets`, `get_overdue_orders`, and `get_recent_notes`.
- Tool Registry Demo calling `search_policy_docs` with policy evidence in JSON output.
- Side-by-side screenshot of `/demo` and a terminal showing `py -m scripts.run_eval` passing.

---

## Recommended next extensions

1. Add real Anthropic / Gemini provider adapters.
2. Connect the MCP server to Claude Desktop or Claude Code.
3. Add OIDC authentication in front of the existing tenant/role context.
4. Connect an external OpenTelemetry collector and production dashboards.
5. Add n8n workflow triggers with approval gates.
6. Add sandboxed Slack / Gmail / CRM adapters.
7. Calibrate an optional LLM-as-judge against human-reviewed examples.
