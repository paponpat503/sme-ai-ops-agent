from __future__ import annotations

import json
from pathlib import Path

from app.security.context import PrincipalContext
from app.tools.registry import call_registered_tool


DATASET = Path(__file__).resolve().parents[1] / "eval" / "security_cases.json"


def run_eval() -> bool:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        principal = PrincipalContext(case["tenant"], "eval", frozenset(case["roles"]), case["id"])
        result = call_registered_tool(case["tool"], case["arguments"], principal)
        allowed = result.error is None
        empty_ok = not case.get("expect_empty") or result.result == []
        case_pass = allowed == case["allowed"] and empty_ok
        passed += int(case_pass)
        print(f"{case['id']} :: {'PASS' if case_pass else 'FAIL'}")
    print(f"Security eval: {passed}/{len(cases)}")
    return passed == len(cases) and len(cases) >= 30


if __name__ == "__main__":
    raise SystemExit(0 if run_eval() else 1)
