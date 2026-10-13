"""Performance budget (build plan section 9): recorded in results/performance.json."""

from __future__ import annotations

import pytest

from madkhal.api.performance import BUDGET_S, measure_advisory
from madkhal.core import paths
from madkhal.core.jsonio import read_json

ROOT = paths.repo_root()


@pytest.mark.req("MK-X-009")
def test_recorded_budget_covers_all_five_measures_and_is_met() -> None:
    res = read_json(ROOT / "results" / "performance.json")
    assert set(res["budget"]) == set(BUDGET_S)
    for key, row in res["budget"].items():
        assert row["budget_s"] == BUDGET_S[key]
        assert row["observed_s"] is not None, f"{key} was not measured"
        assert row["within"] is True, f"{key}: {row['observed_s']} s over {row['budget_s']} s"


@pytest.mark.req("MK-X-009")
def test_recorded_suite_time_is_the_run_that_wrote_the_results() -> None:
    res = read_json(ROOT / "results" / "performance.json")
    run = read_json(ROOT / "results" / "run.json")
    assert res["budget"]["experiment_suite"]["observed_s"] == run["seconds_total"]


@pytest.mark.slow
@pytest.mark.req("MK-X-009")
def test_one_advisory_is_measured_under_budget_now() -> None:
    assert measure_advisory(repeats=5)["max"] < BUDGET_S["advisory_one"]
