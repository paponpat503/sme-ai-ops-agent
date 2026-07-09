from __future__ import annotations

from app.agents.llm_ops_agent import answer_with_agent_result
from rich import print_json


QUESTION = "Which customers need follow-up today?"


def run_smoke_test() -> None:
    result = answer_with_agent_result(QUESTION)
    print(f"QUESTION: {QUESTION}")
    print(f"provider_used: {result.metadata.provider_used}")
    print(f"fallback_used: {result.metadata.fallback_used}")
    print(f"validation_status: {result.metadata.validation_status}")
    if result.metadata.error:
        print(f"error: {result.metadata.error}")
    print_json(data=result.answer.model_dump())


if __name__ == "__main__":
    run_smoke_test()
