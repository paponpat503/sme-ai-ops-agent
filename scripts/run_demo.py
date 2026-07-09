from app.agents.llm_ops_agent import answer_with_agent
from rich import print_json

questions = [
    "Which customers need follow-up today?",
    "Which enterprise accounts are risky?",
    "What is our refund policy for annual subscriptions?",
]
for q in questions:
    print("\n" + "=" * 80)
    print(f"QUESTION: {q}")
    answer = answer_with_agent(q)
    print_json(data=answer.model_dump())
