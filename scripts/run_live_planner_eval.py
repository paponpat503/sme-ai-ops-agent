from __future__ import annotations

import argparse
import os

from app.agents.llm_tool_planner import generate_tool_plan
from app.llm.providers import get_llm_provider
from app.security.context import DEFAULT_PRINCIPAL


QUESTIONS = (
    "Which customers need follow-up today?",
    "Which enterprise accounts are risky?",
    "What is the annual refund policy?",
    "Show overdue orders for C003.",
    "Find open support tickets for C001.",
    "Retrieve recent CRM notes for C003.",
    "Search the onboarding playbook for production checks.",
    "Find the profile for customer C001.",
    "Which accounts have unresolved support risk?",
    "What evidence is required for an enterprise refund?",
)


def run(runs: int = 3) -> bool:
    if os.getenv("RUN_LIVE_LLM_EVAL") != "1":
        raise SystemExit("Set RUN_LIVE_LLM_EVAL=1 to acknowledge live provider usage and cost.")
    provider = get_llm_provider()
    if not provider.is_configured():
        raise SystemExit("The configured LLM provider is unavailable.")
    passed = 0
    total = len(QUESTIONS) * runs
    for run_number in range(1, runs + 1):
        for index, question in enumerate(QUESTIONS, 1):
            try:
                generate_tool_plan(question, provider, DEFAULT_PRINCIPAL)
                valid = True
            except ValueError:
                valid = False
            passed += int(valid)
            print(f"run={run_number} question={index:02d} :: {'PASS' if valid else 'FAIL'}")
    rate = passed / total
    print(f"Live valid-plan rate: {rate:.3f} ({passed}/{total})")
    return rate >= 0.95


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, choices=range(1, 6))
    args = parser.parse_args()
    raise SystemExit(0 if run(args.runs) else 1)
