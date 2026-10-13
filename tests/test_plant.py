from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from madkhal.contract import EvidenceLevel, ParamSource
from madkhal.plant import (
    PlantState,
    default_profile,
    planned_cleaning,
    sample_params,
    simulate,
    tornado,
)

PROFILE = default_profile()
NOM = sample_params(PROFILE, 1, mode="nominal")


def run(
    load: np.ndarray, q: np.ndarray | float, mode: str = "full", f0: float = 0.2, s0: float = 24.0
) -> PlantState:
    n = load.shape[0]
    params = sample_params(PROFILE, n, mode="nominal")
    qq = np.full(n, q) if np.isscalar(q) else np.asarray(q)
    return simulate(params, load, qq, PlantState.initial(n, params, f0, s0), mode)


@pytest.mark.req("MK-L3-001")
def test_profile_is_hypothetical() -> None:
    assert PROFILE.hypothetical is True
    assert "resembles no real asset" in PROFILE.description


@pytest.mark.req("MK-L3-002")
def test_every_parameter_carries_provenance_and_assumption_spread() -> None:
    for p in PROFILE.parameters:
        assert p.evidence_level == EvidenceLevel.L0
        assert p.source == ParamSource.assumption
        assert p.provenance.startswith("ASSUMPTION")
        assert p.rel_spread >= 0.25
        assert p.unit


@pytest.mark.req("MK-L3-008")
def test_assumption_share_is_reported() -> None:
    assert PROFILE.assumption_share == 1.0
    assert PROFILE.evidence_level == EvidenceLevel.L0


@pytest.mark.req("MK-L3-003")
@settings(max_examples=30, deadline=None)
@given(
    st.lists(st.floats(0.0, 4.0), min_size=24, max_size=24),
    st.floats(0.0, 1.0),
    st.floats(0.0, 36.0),
)
def test_water_and_load_balance(loads: list[float], q: float, s0: float) -> None:
    load = np.array([loads])
    params = sample_params(PROFILE, 1, mode="nominal")
    st0 = PlantState.initial(1, params, 0.2, s0)
    start_storage = float(st0.storage[0])
    out = simulate(params, load, np.array([q]), st0, "full")
    lhs = start_storage + out.produced[0]
    rhs = out.delivered[0] + out.storage[0] + out.curtailed[0]
    assert np.isclose(lhs, rhs, rtol=1e-9, atol=1e-6)
    demand_total = float(params.demand[0]) * 24
    assert np.isclose(out.delivered[0] + out.unserved[0], demand_total, rtol=1e-9)
    assert np.isclose(
        out.load_in[0], out.load_removed[0] + out.breakthrough[0], rtol=1e-9, atol=1e-12
    )


@pytest.mark.req("MK-L3-004")
@settings(max_examples=40, deadline=None)
@given(st.floats(0.0, 3.0), st.floats(0.0, 3.0), st.sampled_from([1.0, 0.9, 0.7, 0.5, 0.3]))
def test_higher_load_never_lowers_fouling(a: float, b: float, q: float) -> None:
    lo, hi = sorted((a, b))
    load = np.array([[0.35 + lo] * 72, [0.35 + hi] * 72])
    # Fouling up to the hard limit: once the limit is reached the plant trips and stops
    # accruing breakthrough, so the comparison is on the capped index and the breach time.
    out = run(load, q, mode="decision")
    assert min(out.fouling[1], 1.0) >= min(out.fouling[0], 1.0) - 1e-12
    assert out.breach_hour[1] <= out.breach_hour[0]
    for h in (6, 24, 48):
        part = run(load[:, :h], q, mode="decision")
        assert min(part.fouling[1], 1.0) >= min(part.fouling[0], 1.0) - 1e-12


@pytest.mark.req("MK-L3-004")
@settings(max_examples=40, deadline=None)
@given(st.floats(0.0, 4.0), st.floats(0.0, 1.0), st.floats(0.0, 1.0))
def test_lower_scale_never_raises_fouling(extra: float, a: float, b: float) -> None:
    lo, hi = sorted((a, b))
    load = np.full((2, 72), 0.35 + extra)
    out = run(load, np.array([lo, hi]), mode="decision")
    # As in the load test above: compare the index capped at the hard limit and the breach
    # time. The raw dose is not monotone at the trip boundary, because the hour that trips
    # the plant overshoots the limit by an amount that depends on the scale (D-012).
    assert min(out.fouling[0], 1.0) <= min(out.fouling[1], 1.0) + 1e-12
    assert out.breach_hour[0] >= out.breach_hour[1]


@pytest.mark.req("MK-L3-005")
@settings(max_examples=30, deadline=None)
@given(st.floats(0.0, 1.0), st.floats(0.0, 36.0), st.floats(0.0, 4.0))
def test_storage_never_negative_and_shortfall_only_when_empty(
    q: float, s0: float, extra: float
) -> None:
    params = sample_params(PROFILE, 1, mode="nominal")
    stt = PlantState.initial(1, params, 0.2, s0)
    load = np.full((1, 1), 0.35 + extra)
    for _ in range(96):
        before = stt.unserved.copy()
        simulate(params, load, np.array([q]), stt, "full")
        assert stt.storage[0] >= 0.0
        if stt.unserved[0] > before[0] + 1e-9:
            assert stt.storage[0] <= 1e-9


@pytest.mark.req("MK-L3-006")
def test_same_seed_same_output() -> None:
    def once() -> PlantState:
        rng = np.random.default_rng(3)
        params = sample_params(PROFILE, 50, rng, mode="two_sided")
        load = 0.35 + params.bloom_load(rng.random(50))[:, None] * np.ones((1, 48))
        return simulate(params, load, np.full(50, 0.8), PlantState.initial(50, params), "full")

    a, b = once(), once()
    for k in ("fouling", "storage", "unserved", "produced", "forced_shutdowns"):
        assert np.array_equal(getattr(a, k), getattr(b, k))


@pytest.mark.req("MK-L3-007")
def test_zero_bloom_year_never_forces_a_shutdown() -> None:
    rng = np.random.default_rng(5)
    params = sample_params(PROFILE, 20, rng, mode="two_sided")
    stt = PlantState.initial(20, params)
    for _ in range(365):
        simulate(
            params, np.repeat(params.background_load[:, None], 24, axis=1), np.ones(20), stt, "full"
        )
        planned_cleaning(stt, params)
    assert np.all(stt.forced_shutdowns == 0)


@pytest.mark.req("MK-L3-009")
def test_hard_limit_forces_shutdown_cleaning_and_restart() -> None:
    load = np.full((1, 60), 3.0)
    out = run(load, 1.0, mode="full")
    assert out.forced_shutdowns[0] >= 1
    assert out.cleanings[0] >= 1
    clean_plus_restart = float(NOM.clean_hours[0] + NOM.restart_hours[0])
    assert out.restarts[0] >= 1
    # after the trip the plant produced nothing for the cleaning and restart time
    hours_online = out.produced[0] / float(NOM.design_flow[0])
    assert hours_online <= 60 - clean_plus_restart + 1e-9 or out.forced_shutdowns[0] > 1


@pytest.mark.req("MK-L3-009")
def test_decision_mode_keeps_a_breached_lane_offline() -> None:
    load = np.full((1, 72), 3.0)
    out = run(load, 1.0, mode="decision")
    assert np.isfinite(out.breach_hour[0])
    assert out.forced_shutdowns[0] == 1
    produced_hours = out.produced[0] / float(NOM.design_flow[0])
    assert produced_hours == pytest.approx(out.breach_hour[0])


@pytest.mark.req("MK-L3-010")
def test_sensitivity_ranks_parameters() -> None:
    rows = tornado(PROFILE)
    assert [r.rank for r in rows] == list(range(1, len(rows) + 1))
    assert rows[0].score >= rows[-1].score
    keys = {r.key for r in rows[:5]}
    assert "plant.pretreat_capacity" in keys or "plant.bloom_load_min" in keys
