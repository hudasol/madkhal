"""Policy lab tests. Development seeds only (below 1000); evaluation seeds are never used here."""

from __future__ import annotations

import datetime as dt
import inspect
import subprocess
from dataclasses import replace

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from madkhal.contract import ActionKind, Limits, PlantState
from madkhal.core import paths
from madkhal.decision import (
    CostWeights,
    DecisionInputs,
    SurveyConfig,
    assess,
    risk_table,
    value_of_information,
)
from madkhal.estimator import AT_I, AT_V, CLEAR, DEV_V, SurveySensor, draw_parameters, survey_update
from madkhal.lab import generators, policies
from madkhal.lab.advise import TableCache
from madkhal.lab.experiments import compare
from madkhal.lab.generators import truth_detector, world
from madkhal.lab.inputs import prior_spec
from madkhal.lab.simulation import run_policy
from madkhal.plant import PlantState as SimState
from madkhal.plant import default_profile, sample_params

DEV = (11, 12, 13, 14)
CACHE = TableCache()


def short(gen: str, seeds: tuple[int, ...] = DEV, days: int = 240) -> list[generators.World]:
    return [generators.GENERATORS[gen](s, days) for s in seeds]


# ---------------------------------------------------------------- generators
@pytest.mark.req("MK-L5-001")
def test_g1_uses_posterior_means_and_real_coverage() -> None:
    tr = truth_detector()
    dr = draw_parameters(prior_spec("kalba"), 4000, 7)
    assert tr.alpha[0] == pytest.approx(dr.alpha.mean())
    assert tr.visible_share[0] == pytest.approx(dr.visible_share.mean())
    w = world("G1", 21)
    assert w.days == 730
    assert 0.4 < w.clear.mean() < 0.65  # Kalba's real clear share is about 0.53
    assert "shares the estimator's assumptions" in (generators.__doc__ or "") or "shares" in (
        generators.__doc__ or ""
    )


@pytest.mark.req("MK-L5-002")
def test_g2_is_structurally_different() -> None:
    seeds = range(30, 40)
    g1s = [world("G1", s) for s in seeds]
    g2s = [world("G2", s) for s in seeds]
    summer = np.array([d.month in (6, 7, 8, 9) for d in g1s[0].dates])
    assert np.mean([w.clear[summer].mean() for w in g2s]) < 0.6 * np.mean(
        [w.clear[summer].mean() for w in g1s]
    )
    # same seeds with and without the extra species stream and the heavier tail
    base_rate, base_tail = generators.G2_SPECIES_RATE, generators.G2_TAIL_FACTOR
    try:
        generators.G2_SPECIES_RATE = 1e-9
        generators.G2_TAIL_FACTOR = 1.0
        plain = [world("G2", s) for s in seeds]
    finally:
        generators.G2_SPECIES_RATE, generators.G2_TAIL_FACTOR = base_rate, base_tail
    extra = [
        int((a.at_intake & ~a.visible).sum()) - int((b.at_intake & ~b.visible).sum())
        for a, b in zip(g2s, plain, strict=True)
    ]
    assert all(e >= 0 for e in extra) and sum(extra) > 0
    at = np.zeros(60, dtype=bool)
    at[5:15] = at[30:40] = True
    u = np.random.default_rng(0).random(8)
    plant = generators.truth_plant(31)
    light = generators._episode_loads(at, plant, u, 1.0)
    heavy = generators._episode_loads(at, plant, u, generators.G2_TAIL_FACTOR)
    assert np.all(heavy >= light) and np.any(heavy > light)

    def consecutive_false(ws: list[generators.World]) -> float:
        n = 0
        for w in ws:
            fa = w.alert & ~w.visible
            n += int((fa[1:] & fa[:-1]).sum())
        return n / max(1, sum(int((w.alert & ~w.visible).sum()) for w in ws))

    assert consecutive_false(g2s) > consecutive_false(g1s)


# ---------------------------------------------------------------- policies
@pytest.mark.req("MK-L5-003")
@pytest.mark.parametrize("policy", policies.POLICIES)
def test_every_policy_runs(policy: str) -> None:
    r = run_policy(policy, short("G1", (11, 12), 120), cache=CACHE)
    assert r.policy == policy
    for k in (
        "unserved_m3",
        "forced_shutdowns",
        "cleanings",
        "membrane_index",
        "park_days_per_year",
        "derate_days_per_year",
        "changes_per_30_days",
        "sorties_per_year",
        "weighted_cost_cu",
    ):
        assert r.metrics[k].shape == (2,)


@pytest.mark.req("MK-L5-005")
def test_policies_are_pure_functions() -> None:
    alerts = np.array([False, True, False])
    before = alerts.copy()
    assert policies.alert_park(alerts) == policies.alert_park(alerts)
    assert np.array_equal(alerts, before)
    day = dt.date(2021, 9, 1)
    assert policies.seasonal_rule(day) == policies.seasonal_rule(day)
    assert policies.seasonal_rule(day).action == ActionKind.DERATE
    dr = draw_parameters(prior_spec("kalba"), 50, 7)
    ctx = policies.MadkhalContext("kalba", dr, default_profile(), Limits(), 7)
    b = np.tile(np.array([0.9, 0.03, 0.02, 0.03, 0.02]), (50, 1))
    b0 = b.copy()
    a = policies.madkhal(ctx, day, 244, b, PlantState(), CACHE)
    c = policies.madkhal(ctx, day, 244, b, PlantState(), TableCache())
    assert a == c and np.array_equal(b, b0)
    params = sample_params(default_profile(), 3, mode="nominal")
    stt = SimState.initial(3, params)
    f0 = stt.fouling.copy()
    load = np.full((3, 72), 1.5)
    q1 = policies.oracle(params, stt, load, CostWeights())
    q2 = policies.oracle(params, stt, load, CostWeights())
    assert np.array_equal(q1, q2) and np.array_equal(stt.fouling, f0)
    for fn in (
        policies.always_go,
        policies.alert_park,
        policies.seasonal_rule,
        policies.madkhal,
        policies.oracle,
    ):
        assert "global" not in inspect.getsource(fn)


@pytest.mark.req("MK-L5-006")
def test_oracle_is_never_worse_in_expectation() -> None:
    ws = short("G1", (15, 16, 17, 18, 19, 20), 240)
    costs = {
        p: run_policy(p, ws, cache=CACHE).metrics["weighted_cost_cu"] for p in policies.POLICIES
    }
    for p in policies.POLICIES:
        assert costs["P5"].mean() <= costs[p].mean() + 1e-6, p


@pytest.mark.slow
@pytest.mark.req("MK-L5-004")
def test_metrics_are_reported_separately_with_weights_and_sensitivity() -> None:
    ws = short("G1", (11, 12), 90)
    from madkhal.lab.experiments import _merge, _policy_task

    runs = {p: _merge([_policy_task(("G1", p, [11, 12], {}))]) for p in policies.POLICIES}
    _ = ws
    out = compare(runs, "G1")
    assert set(out["policies"]["P3"]["metrics"]) >= {
        "unserved_m3",
        "forced_shutdowns",
        "weighted_cost_cu",
    }
    assert out["weights"]["forced_shutdown"] == 40_000.0
    assert len(out["weight_sensitivity"]) == 12
    assert "regret_cu" in out["policies"]["P0"]


@pytest.mark.req("MK-L5-010")
def test_preregistration_precedes_every_results_file() -> None:
    root = paths.repo_root()

    def first_commit(path: str) -> str | None:
        out = (
            subprocess.run(
                ["git", "log", "--diff-filter=A", "--format=%H %ct", "--", path],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            .stdout.strip()
            .splitlines()
        )
        return out[-1] if out else None

    prereg = first_commit("docs/PREREGISTRATION.md")
    assert prereg is not None, "docs/PREREGISTRATION.md must be committed"
    prereg_time = int(prereg.split()[1])
    results = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%ct", "--", "results/"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    for t in results:
        assert int(t) >= prereg_time


# ---------------------------------------------------------------- inspection value
def _vinputs(p_at: float, seed: int = 3) -> DecisionInputs:
    d = 40
    rng = np.random.default_rng(seed)
    at = np.clip(p_at * np.exp(0.4 * rng.standard_normal(d)), 0, 0.9)
    b = np.stack([1 - at - 0.02, np.full(d, 0.02), at], axis=1)
    return DecisionInputs(
        site="t",
        issued_for=dt.datetime(2021, 9, 1, 2, tzinfo=dt.UTC),
        belief=b,
        hazard=np.full((d, 8), 0.004),
        p_da=np.full(d, 0.2),
        p_dc=np.full(d, 0.1),
        p_ac=np.full(d, 0.07),
        profile=default_profile(),
        state=PlantState(),
        limits=Limits(),
        seed=seed,
    )


@pytest.mark.req("MK-L6-007")
@settings(max_examples=25, deadline=None)
@given(st.floats(0.0, 0.8), st.floats(0.0, 0.3), st.floats(0.3, 1.0), st.floats(0.5, 1.0))
def test_value_of_information_is_never_negative(
    p_at: float, fp: float, pdev: float, pat: float
) -> None:
    inp = _vinputs(p_at)
    sensor = SurveySensor(p_clear=fp, p_developing=pdev, p_at_intake=pat)
    voi, _ = value_of_information(inp, risk_table(inp), SurveyConfig(sensor=sensor))
    assert voi >= 0.0


@pytest.mark.req("MK-L6-008")
@settings(max_examples=20, deadline=None)
@given(st.floats(0.0, 0.8))
def test_perfect_free_sensor_inspects_whenever_decision_could_change(p_at: float) -> None:
    inp = _vinputs(p_at)
    cfg = SurveyConfig(sensor=SurveySensor(0.0, 1.0, 1.0), availability=1.0, cost_cu=0.0)
    a = assess(inp, risk_table(inp), cfg)
    assert a.inspect == a.decision_could_change


@pytest.mark.req("MK-L4-013")
def test_inspect_needs_value_above_cost_and_ignores_staleness() -> None:
    inp = _vinputs(0.3)
    table = risk_table(inp)
    cheap = assess(inp, table, SurveyConfig(cost_cu=1.0, availability=1.0))
    dear = assess(inp, table, SurveyConfig(cost_cu=1e9, availability=1.0))
    assert not dear.inspect
    assert cheap.break_even_cost_cu == pytest.approx(cheap.value_cu)
    assert cheap.inspect == (cheap.value_cu > 1.0)
    # the value depends on the belief only, not on how old the last clear view is
    stale = replace(inp, state=PlantState(hours_in_action=5000.0))
    assert assess(
        stale, table, SurveyConfig(cost_cu=1.0, availability=1.0)
    ).value_cu == pytest.approx(cheap.value_cu)


@pytest.mark.req("MK-L2-013")
def test_survey_update_moves_belief_the_right_way() -> None:
    b = np.tile(np.array([0.8, 0.05, 0.05, 0.05, 0.05]), (10, 1))
    s = SurveySensor()
    up = survey_update(b, True, s)
    down = survey_update(b, False, s)
    assert np.all(up[:, CLEAR] < b[:, CLEAR]) and np.all(down[:, CLEAR] > b[:, CLEAR])
    assert np.allclose(up.sum(axis=1), 1.0)
    # the survey sees blooms the satellite cannot: invisible states move like visible ones
    assert np.allclose(up[:, AT_I], up[:, AT_V]) and up[0, DEV_V] > b[0, DEV_V]
