from __future__ import annotations

import json
from pathlib import Path

from app.rag.runtime import rag_runtime


EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


def run_eval() -> bool:
    if not rag_runtime.is_ready():
        rag_runtime.build()
    cases = []
    for path in sorted(EVAL_DIR.glob("retrieval_cases*.json")):
        cases.extend(json.loads(path.read_text(encoding="utf-8")))
    if len(cases) < 75:
        raise ValueError(f"Retrieval dataset must contain at least 75 cases, found {len(cases)}.")
    answerable = [case for case in cases if case["expected_source"]]
    negatives = [case for case in cases if not case["expected_source"]]
    reciprocal_ranks: list[float] = []
    recall_hits = 0
    abstentions = 0
    for case in cases:
        hits = rag_runtime.search(case["query"], top_k=5)
        expected = case["expected_source"]
        if expected is None:
            passed = not hits
            abstentions += int(passed)
        else:
            rank = next((index for index, hit in enumerate(hits, 1) if hit.source == expected), None)
            passed = rank is not None
            recall_hits += int(passed)
            reciprocal_ranks.append(0.0 if rank is None else 1.0 / rank)
        print(f"{case['id']} :: {'PASS' if passed else 'FAIL'}")

    recall = recall_hits / len(answerable)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    abstention_precision = abstentions / len(negatives)
    print(f"Recall@5: {recall:.3f}")
    print(f"MRR@5: {mrr:.3f}")
    print(f"Negative abstention: {abstention_precision:.3f}")
    return recall >= 0.90 and mrr >= 0.80 and abstention_precision >= 0.90


if __name__ == "__main__":
    raise SystemExit(0 if run_eval() else 1)
