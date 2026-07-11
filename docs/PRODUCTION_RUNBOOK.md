# Production Runbook

## Release Gate

```powershell
py -m compileall app scripts mcp
py -m pytest -q
py -m scripts.run_eval
py -m scripts.run_retrieval_eval
py -m scripts.run_planner_eval
py -m scripts.run_security_eval
py -m scripts.run_mcp_smoke_test
py -m scripts.run_dashboard_smoke_test
py -m scripts.run_tool_agent_smoke_test
```

The MCP test launches a real stdio server and requires operating-system permission to create a subprocess.

The offline release gate contains 150 versioned cases: 75 retrieval, 30 planner, 30 security, and 15 end-to-end cases. CI also starts PostgreSQL with pgvector, applies all migrations, and runs the vector integration contract.

Live release candidates require explicit cost opt-in and provider credentials:

```powershell
$env:RUN_LIVE_LLM_EVAL = "1"
py -m scripts.run_live_planner_eval --runs 3
py -m scripts.run_live_llm_eval --runs 3
```

The live planner gate requires at least 95% valid plans. The live end-to-end gate requires at least 90% grounded, non-fallback task success. These commands are never part of credential-free CI.

## Health and Recovery

- Use `/live` for process monitoring.
- Use `/ready` for traffic routing.
- Inspect `/ready.checks` to distinguish retrieval, data, and tool-transport failures.
- A provider failure should return a deterministic result with `fallback_used=true`.
- An MCP failure is returned as a controlled tool error; switch `TOOL_TRANSPORT=local` to restore service.
- If retrieval is unavailable, `/ready` returns 503 and policy answers abstain.
- If the LLM circuit opens, requests use deterministic fallback until the configured cooldown expires.
- Set `OTEL_EXPORTER_OTLP_ENDPOINT` to export traces; otherwise spans remain local and no telemetry leaves the process.

API tool-call failures retain a stable JSON envelope with `error_code`. Treat `403` as a policy decision, `422` as caller correction, and `502` as a dependency incident. Rate-limit responses return `429`, `Retry-After`, and `X-RateLimit-*` headers.

## Public Demo

Use synthetic data only. Keep the demo tenant isolated, cap provider spend externally, rotate `APP_API_KEY`, and leave tool writes restricted to the fake task tool. Verify desktop and mobile dashboard layouts after every CSS or response-schema change.

## Rollback

Redeploy the previous known-good Render commit. Restore `TOOL_TRANSPORT=local`, `TOOL_PLANNER=deterministic`, and `AGENT_MODE=auto` first when isolating an orchestration incident.
