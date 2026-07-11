import json
from pathlib import Path


def test_retrieval_dataset_has_unique_ids_and_required_coverage():
    cases = []
    for path in Path("eval").glob("retrieval_cases*.json"):
        cases.extend(json.loads(path.read_text(encoding="utf-8")))
    ids = [case["id"] for case in cases]
    assert len(cases) >= 75
    assert len(ids) == len(set(ids))
    assert sum(case["expected_source"] is None for case in cases) >= 15
    assert {case["expected_source"] for case in cases if case["expected_source"]} == {
        "company_policy.md",
        "onboarding_playbook.md",
    }
