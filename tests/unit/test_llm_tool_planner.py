import json

from app.agents.llm_tool_planner import generate_tool_plan
from app.llm.providers import LLMResult
from app.security.context import PrincipalContext


class FakeProvider:
    name = "fake"
    def is_configured(self):
        return True
    def generate(self, prompt):
        payload = {
            "calls": [
                {
                    "tool_name": "search_policy_docs",
                    "arguments": {"query": "refund policy", "top_k": 2},
                    "reason": "Retrieve policy evidence",
                    "depends_on": [],
                }
            ]
        }
        return LLMResult(provider="fake", text=json.dumps(payload), available=True)


def test_llm_plan_is_parsed_and_validated():
    principal = PrincipalContext("demo", "user", frozenset({"viewer"}), "test")
    plan = generate_tool_plan("What is the refund policy?", FakeProvider(), principal)
    assert plan.calls[0].tool_name == "search_policy_docs"
