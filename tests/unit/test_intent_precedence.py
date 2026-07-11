from app.agents.ops_agent import answer_with_deterministic_agent


def test_policy_intent_precedes_customer_keywords():
    answer = answer_with_deterministic_agent("Explain the enterprise refund policy")
    assert answer.intent == "knowledge_retrieval"


def test_customer_followup_policy_is_treated_as_knowledge_request():
    answer = answer_with_deterministic_agent("What is the policy for high-risk customer follow-up?")
    assert answer.intent == "knowledge_retrieval"
