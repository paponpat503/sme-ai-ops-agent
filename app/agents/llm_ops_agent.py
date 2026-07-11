from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from app.agents.ops_agent import answer_with_deterministic_agent
from app.agents.tool_agent import answer_with_tool_agent
from app.llm.output_validation import AgentOutputError, parse_and_validate_agent_answer
from app.llm.providers import get_llm_provider
from app.rag.runtime import rag_runtime
from app.schemas.models import AgentAnswer, AgentRunMetadata, ToolAgentTrace
from app.tools.crm_tools import (
    load_crm_notes,
    load_customers,
    load_orders,
    load_tickets,
)
from app.security.context import get_principal
from app.observability import emit_event
from app.telemetry import get_tracer

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "structured_output_prompt.md"
SUPPORTED_AGENT_MODES = {"deterministic", "llm", "auto", "tool_agent"}


@dataclass(frozen=True)
class AgentRunResult:
    answer: AgentAnswer
    metadata: AgentRunMetadata
    tool_trace: ToolAgentTrace | None = None


def answer_with_agent(question: str) -> AgentAnswer:
    return answer_with_agent_result(question).answer


def answer_with_agent_result(question: str) -> AgentRunResult:
    started = time.perf_counter()
    principal = get_principal()
    with get_tracer().start_as_current_span("agent.run") as span:
        span.set_attribute("tenant.id", principal.tenant_id)
        span.set_attribute("request.id", principal.request_id)
        result = _answer_with_agent_result(question)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        metadata = result.metadata.model_copy(
            update={
                "request_id": principal.request_id,
                "tenant_id": principal.tenant_id,
                "latency_ms": latency_ms,
            }
        )
        span.set_attribute("agent.mode", metadata.agent_mode)
        span.set_attribute("agent.provider", metadata.provider_used)
        span.set_attribute("agent.fallback", metadata.fallback_used)
        span.set_attribute("agent.tool_calls", metadata.tool_calls_count)
    emit_event(
        "agent_run",
        request_id=principal.request_id,
        tenant_id=principal.tenant_id,
        mode=metadata.agent_mode,
        provider=metadata.provider_used,
        fallback_used=metadata.fallback_used,
        fallback_reason=metadata.fallback_reason,
        latency_ms=latency_ms,
        tool_calls=metadata.tool_calls_count,
    )
    return AgentRunResult(answer=result.answer, metadata=metadata, tool_trace=result.tool_trace)


def _answer_with_agent_result(question: str) -> AgentRunResult:
    mode = _get_agent_mode()
    if mode == "deterministic":
        return _deterministic_result(question, mode)
    if mode == "tool_agent":
        return _tool_agent_result(question)

    provider = get_llm_provider()
    if mode == "auto" and not provider.is_configured():
        return _deterministic_result(question, mode)

    if not provider.is_configured():
        return _fallback_result(
            question=question,
            mode=mode,
            provider_used=provider.name,
            validation_status="provider_unavailable",
            error=f"{provider.name} is not configured.",
        )

    prompt = build_structured_output_prompt(question)
    result = provider.generate(prompt)
    if not result.available or not result.text:
        return _fallback_result(
            question=question,
            mode=mode,
            provider_used=result.provider,
            validation_status="provider_unavailable",
            error=result.error,
        )

    try:
        answer = parse_and_validate_agent_answer(result.text)
        return AgentRunResult(
            answer=answer,
            metadata=AgentRunMetadata(
                agent_mode=mode,
                provider_used=result.provider,
                fallback_used=False,
                validation_status="valid",
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                estimated_cost_usd=result.estimated_cost_usd,
            ),
        )
    except AgentOutputError as exc:
        return _fallback_result(
            question=question,
            mode=mode,
            provider_used=result.provider,
            validation_status="invalid_fallback",
            error=str(exc),
        )


def build_structured_output_prompt(question: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    hits = rag_runtime.search(question, top_k=3)
    retrieved_context = [
        {
            "source": hit.source,
            "doc_id": hit.doc_id,
            "score": round(hit.score, 4),
            "text": hit.text,
        }
        for hit in hits
    ]
    return (
        template.replace("{question}", question)
        .replace("{retrieved_context}", json.dumps(retrieved_context, indent=2))
        .replace("{structured_records}", json.dumps(_load_structured_records(), indent=2))
    )


def _load_structured_records() -> dict:
    return {
        "customers": load_customers().to_dict(orient="records"),
        "tickets": load_tickets().to_dict(orient="records"),
        "orders": load_orders().to_dict(orient="records"),
        "crm_notes": load_crm_notes().to_dict(orient="records"),
    }


def _get_agent_mode() -> str:
    mode = os.getenv("AGENT_MODE", "auto").strip().lower()
    if mode not in SUPPORTED_AGENT_MODES:
        return "auto"
    return mode


def _deterministic_result(question: str, mode: str) -> AgentRunResult:
    return AgentRunResult(
        answer=answer_with_deterministic_agent(question),
        metadata=AgentRunMetadata(
            agent_mode=mode,
            provider_used="deterministic",
            fallback_used=False,
            validation_status="not_attempted",
        ),
    )


def _fallback_result(
    question: str,
    mode: str,
    provider_used: str,
    validation_status: str,
    error: str | None = None,
) -> AgentRunResult:
    return AgentRunResult(
        answer=answer_with_deterministic_agent(question),
        metadata=AgentRunMetadata(
            agent_mode=mode,
            provider_used=provider_used,
            fallback_used=True,
            validation_status=validation_status,
            error=error,
            fallback_reason=validation_status,
        ),
    )


def _tool_agent_result(question: str) -> AgentRunResult:
    result = answer_with_tool_agent(question)
    tools_called = [item.tool_name for item in result.trace.results]
    return AgentRunResult(
        answer=result.answer,
        metadata=AgentRunMetadata(
            agent_mode="tool_agent",
            provider_used="tool_agent",
            fallback_used=result.fallback_used,
            validation_status="valid" if not result.fallback_used else "invalid_fallback",
            error=result.error,
            tool_agent_used=True,
            tool_calls_count=len(tools_called),
            tools_called=tools_called,
        ),
        tool_trace=result.trace,
    )
