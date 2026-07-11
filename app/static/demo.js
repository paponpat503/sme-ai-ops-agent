const questionInput = document.querySelector("#agent-question");
const runAgentButton = document.querySelector("#run-agent");
const agentError = document.querySelector("#agent-error");
const summaryEl = document.querySelector("#agent-summary");
const confidenceEl = document.querySelector("#agent-confidence");
const riskCardsEl = document.querySelector("#risk-cards");
const metaMode = document.querySelector("#meta-mode");
const metaProvider = document.querySelector("#meta-provider");
const metaFallback = document.querySelector("#meta-fallback");
const metaValidation = document.querySelector("#meta-validation");
const metaError = document.querySelector("#meta-error");
const metaTools = document.querySelector("#meta-tools");
const metaRequest = document.querySelector("#meta-request");
const metaLatency = document.querySelector("#meta-latency");
const metaTokens = document.querySelector("#meta-tokens");
const metaTenant = document.querySelector("#meta-tenant");
const traceCount = document.querySelector("#trace-count");
const toolTraceEl = document.querySelector("#tool-trace");
const toolSelect = document.querySelector("#tool-select");
const toolArgs = document.querySelector("#tool-args");
const callToolButton = document.querySelector("#call-tool");
const toolOutput = document.querySelector("#tool-output");

const defaultArgs = {
  search_customers: { query: "enterprise" },
  get_customer_profile: { customer_id: "C001" },
  get_open_tickets: { customer_id: "C003" },
  get_overdue_orders: { customer_id: "C003" },
  get_recent_notes: { customer_id: "C003", limit: 2 },
  search_policy_docs: { query: "refund policy", top_k: 2 },
  draft_followup_email: {
    customer_name: "ABC Fitness",
    reason: "open checkout ticket and overdue invoice",
    action: "schedule a support call"
  },
  create_crm_task_demo: {
    customer_id: "C003",
    task: "Schedule workflow sync escalation call",
    due_date: "2026-07-10",
    owner: "sales"
  }
};

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { error: text || "Non-JSON response from server." };
  }
  if (!response.ok) {
    throw new Error(data?.detail || data?.error || `HTTP ${response.status}`);
  }
  return data;
}

function setAgentLoading(isLoading) {
  runAgentButton.disabled = isLoading;
  runAgentButton.textContent = isLoading ? "Running..." : "Run Agent";
}

function setToolLoading(isLoading) {
  callToolButton.disabled = isLoading;
  callToolButton.textContent = isLoading ? "Calling..." : "Call Tool";
}

function showAgentError(message) {
  if (!message) {
    agentError.hidden = true;
    agentError.textContent = "";
    return;
  }
  agentError.hidden = false;
  agentError.textContent = message;
}

function renderMetadata(metadata = {}) {
  metaMode.textContent = metadata.agent_mode ?? "-";
  metaProvider.textContent = metadata.provider_used ?? "-";
  metaFallback.textContent = String(metadata.fallback_used ?? "-");
  metaValidation.textContent = metadata.validation_status ?? "-";
  metaError.textContent = metadata.error || "-";
  const tools = Array.isArray(metadata.tools_called) ? metadata.tools_called : [];
  metaTools.textContent = tools.length ? tools.join(", ") : "-";
  metaRequest.textContent = metadata.request_id ?? "-";
  metaTenant.textContent = metadata.tenant_id ?? "-";
  metaLatency.textContent = `${metadata.latency_ms ?? 0} ms`;
  metaTokens.textContent = `${metadata.prompt_tokens ?? 0} in / ${metadata.completion_tokens ?? 0} out`;
}

function renderAgentPayload(payload) {
  const answer = payload.answer || payload;
  const metadata = payload.metadata || {
    provider_used: "unknown",
    fallback_used: "unknown",
    validation_status: "legacy_shape",
    error: null
  };

  renderMetadata(metadata);
  renderToolTrace(payload.tool_trace);
  summaryEl.textContent = answer.summary || "No summary returned.";
  confidenceEl.textContent = `confidence: ${answer.confidence || "unknown"}`;

  const actions = Array.isArray(answer.actions) ? answer.actions : [];
  if (!actions.length) {
    riskCardsEl.className = "risk-list empty-state";
    riskCardsEl.textContent = "No customer actions returned.";
    return;
  }

  riskCardsEl.className = "risk-list";
  riskCardsEl.innerHTML = actions.map(renderRiskCard).join("");
}

function renderToolTrace(trace) {
  const plan = Array.isArray(trace?.plan) ? trace.plan : [];
  const results = Array.isArray(trace?.results) ? trace.results : [];
  traceCount.textContent = `${results.length} calls`;

  if (!plan.length && !results.length) {
    toolTraceEl.className = "trace-list empty-state";
    toolTraceEl.textContent = "Tool trace appears when AGENT_MODE is set to tool_agent.";
    return;
  }

  toolTraceEl.className = "trace-list";
  const traceHeader = `<p class="trace-summary">planner: ${escapeHtml(trace.planner || "deterministic")} | transport: ${escapeHtml(trace.transport || "local")}</p>`;
  toolTraceEl.innerHTML = traceHeader + results.map((result, index) => {
    const planned = plan[index] || {};
    const summary = summarizeToolResult(result.result);
    return `
      <article class="trace-card">
        <header>
          <h3>${escapeHtml(result.tool_name || planned.tool_name || "tool")}</h3>
          <strong class="${result.error ? "trace-error" : "risk-low"}">${result.error ? "error" : "ok"}</strong>
        </header>
        <p class="trace-reason">${escapeHtml(planned.reason || "No planning reason returned.")}</p>
        <p class="trace-summary">${escapeHtml(summary)} (${escapeHtml(String(result.latency_ms ?? 0))} ms)</p>
        ${result.error ? `<p class="trace-error">${escapeHtml(result.error)}</p>` : ""}
        <h3>Arguments</h3>
        <pre>${escapeHtml(JSON.stringify(result.arguments || {}, null, 2))}</pre>
      </article>
    `;
  }).join("");
}

function summarizeToolResult(result) {
  if (Array.isArray(result)) {
    if (!result.length) {
      return "Returned an empty list.";
    }
    const first = result[0];
    const keys = first && typeof first === "object" ? Object.keys(first).slice(0, 4).join(", ") : "primitive values";
    return `Returned ${result.length} item(s). First item keys: ${keys}.`;
  }
  if (result && typeof result === "object") {
    return `Returned object with keys: ${Object.keys(result).slice(0, 6).join(", ")}.`;
  }
  if (result == null) {
    return "No result payload.";
  }
  return String(result).slice(0, 160);
}

function renderRiskCard(action) {
  const evidence = Array.isArray(action.evidence) ? action.evidence : [];
  const riskClass = `risk-${escapeHtml(action.risk_level || "low")}`;
  return `
    <article class="risk-card">
      <header>
        <h3>${escapeHtml(action.customer_name || "Unknown customer")}</h3>
        <strong class="${riskClass}">${escapeHtml(action.risk_level || "-")}</strong>
      </header>
      <div class="risk-meta">
        <span>priority ${escapeHtml(String(action.priority_score ?? "-"))}</span>
        <span>${escapeHtml(action.recommended_action || "-")}</span>
      </div>
      <p>${escapeHtml(action.reason || "No reason returned.")}</p>
      <h3>Evidence</h3>
      <ul class="evidence-list">
        ${evidence.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
      <h3>Draft Message</h3>
      <p class="draft">${escapeHtml(action.draft_message || "No draft returned.")}</p>
    </article>
  `;
}

async function runAgent() {
  setAgentLoading(true);
  showAgentError("");
  try {
    const payload = await apiFetch("/agent/ask", {
      method: "POST",
      body: JSON.stringify({ question: questionInput.value.trim() })
    });
    renderAgentPayload(payload);
  } catch (error) {
    showAgentError(error.message);
  } finally {
    setAgentLoading(false);
  }
}

async function loadTools() {
  const payload = await apiFetch("/tools/list");
  const tools = payload.tools || [];
  toolSelect.innerHTML = tools
    .map((tool) => `<option value="${escapeHtml(tool.name)}">${escapeHtml(tool.name)}</option>`)
    .join("");
  if (tools.length) {
    toolSelect.value = tools.some((tool) => tool.name === "get_open_tickets")
      ? "get_open_tickets"
      : tools[0].name;
    updateToolArgs();
  }
}

function updateToolArgs() {
  const args = defaultArgs[toolSelect.value] || {};
  toolArgs.value = JSON.stringify(args, null, 2);
}

async function callTool() {
  setToolLoading(true);
  try {
    const args = JSON.parse(toolArgs.value || "{}");
    const payload = await apiFetch("/tools/call", {
      method: "POST",
      body: JSON.stringify({ tool_name: toolSelect.value, arguments: args })
    });
    toolOutput.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    toolOutput.textContent = JSON.stringify({ error: error.message }, null, 2);
  } finally {
    setToolLoading(false);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

runAgentButton.addEventListener("click", runAgent);
callToolButton.addEventListener("click", callTool);
toolSelect.addEventListener("change", updateToolArgs);

loadTools()
  .then(runAgent)
  .catch((error) => {
    toolOutput.textContent = JSON.stringify({ error: error.message }, null, 2);
  });
