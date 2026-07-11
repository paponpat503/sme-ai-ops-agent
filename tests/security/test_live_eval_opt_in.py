import pytest

from scripts.run_live_llm_eval import run as run_llm_eval
from scripts.run_live_planner_eval import run as run_planner_eval


def test_live_evals_require_explicit_cost_opt_in(monkeypatch):
    monkeypatch.delenv("RUN_LIVE_LLM_EVAL", raising=False)
    with pytest.raises(SystemExit, match="acknowledge"):
        run_llm_eval(1)
    with pytest.raises(SystemExit, match="acknowledge"):
        run_planner_eval(1)
