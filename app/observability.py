from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


logger = logging.getLogger("sme_ai_ops_agent")


@dataclass
class RunMetrics:
    started_at: float = field(default_factory=time.perf_counter)
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    fallback_reason: str | None = None

    def finish(self) -> None:
        self.latency_ms = round((time.perf_counter() - self.started_at) * 1000, 2)


def emit_event(event: str, **fields: object) -> None:
    safe = {key: value for key, value in fields.items() if key not in {"prompt", "api_key", "tool_result"}}
    logger.info(json.dumps({"event": event, **safe}, default=str, sort_keys=True))


@contextmanager
def timed_stage(stage: str, **fields: object) -> Iterator[dict[str, float]]:
    started = time.perf_counter()
    timing: dict[str, float] = {}
    try:
        yield timing
    finally:
        timing["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        emit_event("stage_complete", stage=stage, latency_ms=timing["latency_ms"], **fields)
