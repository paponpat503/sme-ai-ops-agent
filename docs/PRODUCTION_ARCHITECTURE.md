# Production Architecture

## Trust Boundary

Every request receives a server-generated request ID and a `PrincipalContext` containing tenant, user, and validated roles. Production API routes require `APP_API_KEY` or a typed `APP_API_KEYS_JSON` identity map. Tenant identity is never accepted from a prompt or tool arguments. Tool authorization is enforced in the registry and tenant filtering is enforced again in data and retrieval adapters. The same scoped identity is propagated into MCP subprocess sessions.

The local demo uses a synthetic `demo` tenant and operator. It never connects to a real CRM or sends email.

## Agent Flow

```text
FastAPI request
  -> authenticate and establish PrincipalContext
  -> deterministic or LLM tool planner
  -> strict ToolPlan and per-tool Pydantic validation
  -> capability policy and call-budget checks
  -> local registry or real MCP stdio transport
  -> tenant-scoped data/retrieval adapter
  -> grounded AgentAnswer validation
  -> deterministic fallback on provider or validation failure
  -> correlated metadata and tool trace
```

Executable LLM plans are parsed strictly. JSON repair is intentionally disabled for plans, write tools are rejected, unknown or duplicate calls are rejected, dependencies must point backward, and the default budget is five calls.

## Data and Retrieval

`BusinessRepository` separates orchestration from storage. `CsvBusinessRepository` supports the zero-infrastructure demo. `SqlAlchemyBusinessRepository` supports PostgreSQL and uses tenant ID as part of every primary key and query boundary. PostgreSQL migrations enable row-level security on business and retrieval tables, and each repository transaction installs the server-controlled tenant context. Task writes use stable idempotency keys.

The offline retriever uses stable content-derived chunk IDs, document versions, source metadata, score thresholding, and explicit abstention. Only business knowledge files are indexed. `RETRIEVER_MODE` selects TF-IDF, PostgreSQL/pgvector dense search, or hybrid reciprocal-rank fusion. Vector modes fail readiness unless PostgreSQL, the vector migration, and embeddings are available. The 75-case retrieval gate measures Recall@5, MRR, and negative-query abstention.

## Operations

- `/live` checks process liveness.
- `/ready` reports component-level retrieval, data-adapter, and configured tool-transport readiness.
- API requests are limited to 64 KB and 60 requests per minute per client by default. The limiter is thread-safe, bounded to 10,000 tracked clients, excludes static/health traffic, and returns remaining/retry headers.
- Proxy-derived client addresses are ignored unless `TRUST_PROXY_HEADERS=true`; deployments enabling it must use a trusted proxy that replaces inbound forwarding headers.
- Caller-supplied request IDs are accepted only from a bounded safe character set; invalid values are replaced before tracing or logging.
- Agent metadata includes request ID, tenant, latency, token usage, fallback reason, and tool counts.
- Tool traces identify planner, transport, validation status, and per-call latency.
- Tool API failures use typed codes and HTTP semantics: forbidden `403`, unknown tool `404`, invalid arguments `422`, and dependency execution failure `502`.
- Structured logging excludes prompts, API keys, and complete tool results.
- OpenTelemetry spans cover agent runs, retrieval, and tool execution; an OTLP HTTP exporter activates only when `OTEL_EXPORTER_OTLP_ENDPOINT` is configured.
- Transient LLM failures use bounded exponential backoff, and repeated dependency failures open a process-level circuit breaker.
- Provider usage records input/output tokens and cost from deployment-configured per-million-token rates.

## Production Configuration

Set `APP_ENV=production` and either `APP_API_KEY` or `APP_API_KEYS_JSON` to protect operational endpoints. The JSON key map assigns each credential a server-controlled tenant, user, and role set. Use `TOOL_TRANSPORT=mcp` for real MCP stdio execution, `TOOL_PLANNER=llm` for validated model-generated plans, and `RETRIEVER_MODE=hybrid` for PostgreSQL hybrid retrieval. Keep `AGENT_MODE=auto` to preserve deterministic fallback.

## Known Limits

- Authentication is a deployment API key, not OIDC.
- Dense embeddings and pgvector retrieval are not enabled in the zero-cost demo.
- An external OpenTelemetry collector and alerting backend must be supplied by the deployment.
- Live-model quality and cost gates require provider credentials and are intentionally separate from offline CI.
