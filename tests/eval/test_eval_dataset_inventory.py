import json
from pathlib import Path


def test_versioned_eval_inventory_meets_production_floor():
    counts = {}
    for name in ("eval_cases.json", "planner_cases.json", "security_cases.json", "retrieval_cases.json", "retrieval_cases_extended.json"):
        counts[name] = len(json.loads((Path("eval") / name).read_text(encoding="utf-8")))
    assert counts["planner_cases.json"] >= 30
    assert counts["security_cases.json"] >= 30
    assert counts["retrieval_cases.json"] + counts["retrieval_cases_extended.json"] >= 75
    assert counts["eval_cases.json"] >= 15
    assert sum(counts.values()) >= 150
