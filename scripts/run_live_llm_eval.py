from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

from app.agents.llm_ops_agent import answer_with_agent_result
from app.llm.output_validation import validate_grounding


DATASET = Path(__file__).resolve().parents[1] / "eval" / "eval_cases.json"


def run(runs: int = 3) -> bool:
    if os.getenv("RUN_LIVE_LLM_EVAL") != "1":
        raise SystemExit("Set RUN_LIVE_LLM_EVAL=1 to acknowledge live provider usage and cost.")
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for live LLM evaluation.")
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    previous_mode = os.environ.get("AGENT_MODE")
    os.environ["AGENT_MODE"] = "llm"
    successes = 0
    total = len(cases) * runs
    latencies: list[float] = []
    prompt_tokens = completion_tokens = 0
    cost = 0.0
    try:
        for run_number in range(1, runs + 1):
            for case in cases:
                started = time.perf_counter()
                result = answer_with_agent_result(case["question"])
                latencies.append((time.perf_counter() - started) * 1000)
                prompt_tokens += result.metadata.prompt_tokens
                completion_tokens += result.metadata.completion_tokens
                cost += result.metadata.estimated_cost_usd
                valid = not result.metadata.fallback_used and result.answer.intent == case["expected_intent"]
                names = {action.customer_name for action in result.answer.actions}
                action_types = {action.recommended_action for action in result.answer.actions}
                valid = valid and all(name in names for name in case.get("must_include_customers", []))
                valid = valid and all(name not in names for name in case.get("must_not_include_customers", []))
                valid = valid and all(action in action_types for action in case.get("required_action_types", []))
                try:
                    validate_grounding(result.answer)
                except ValueError:
                    valid = False
                successes += int(valid)
                print(f"run={run_number} {case['id']} :: {'PASS' if valid else 'FAIL'}")
    finally:
        if previous_mode is None:
            os.environ.pop("AGENT_MODE", None)
        else:
            os.environ["AGENT_MODE"] = previous_mode
    rate = successes / total
    print(f"Live success rate: {rate:.3f} ({successes}/{total})")
    print(f"Latency p50: {statistics.median(latencies):.1f} ms")
    print(f"Latency max: {max(latencies):.1f} ms")
    print(f"Tokens: {prompt_tokens} input / {completion_tokens} output")
    print(f"Estimated cost: ${cost:.6f}")
    return rate >= 0.90


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, choices=range(1, 6))
    args = parser.parse_args()
    raise SystemExit(0 if run(args.runs) else 1)
