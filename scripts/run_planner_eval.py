from __future__ import annotations

import json
from pathlib import Path

from app.agents.plan_validation import validate_tool_plan
from app.schemas.models import ToolPlan
from app.security.context import PrincipalContext


DATASET = Path(__file__).resolve().parents[1] / "eval" / "planner_cases.json"


def run_eval() -> bool:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        try:
            principal = PrincipalContext("demo", "eval", frozenset(case["roles"]), case["id"])
            validate_tool_plan(ToolPlan.model_validate({"calls": case["calls"]}), principal)
            valid = True
        except (ValueError, TypeError):
            valid = False
        case_pass = valid == case["valid"]
        passed += int(case_pass)
        print(f"{case['id']} :: {'PASS' if case_pass else 'FAIL'}")
    print(f"Planner eval: {passed}/{len(cases)}")
    return passed == len(cases) and len(cases) >= 30


if __name__ == "__main__":
    raise SystemExit(0 if run_eval() else 1)
