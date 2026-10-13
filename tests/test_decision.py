from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from madkhal.contract import ActionKind, Limits, PlantState, restrictiveness
from madkhal.decision import CANDIDATES, DecisionInputs, decide, evaluate
from madkhal.plant import default_profile

PROFILE = default_profile()
D = 40
WHEN = dt.datetime(2020, 9, 10, 6, tzinfo=dt.UTC)


def make_inputs(
    p_dev: float = 0.05,
    p_at: float = 0.05,
    state: PlantState | None = None,
    limits: Limits | None = None,
    profile=PROFILE,  # type: ignore[no-untyped-def]
    seed: int = 3,
    spread: float = 0.5,
) -> DecisionInputs:
    rng = np.random.default_rng(seed)
    at = np.clip(p_at * np.exp(spread * rng.standard_normal(D)), 0, 0.95)
    dev = np.clip(p_dev * np.exp(spread * rng.standard_normal(D)), 0, 0.95 - at)
    belief = np.stack([1 - dev - at, dev, at], axis=1)
    return DecisionInputs(
        site="test",
        issued_for=WHEN,
        belief=belief,
        hazard=np.full((D, 8), 0.004),
        p_da=np.full(D, 0.2),
        p_dc=np.full(D, 0.1),
        p_ac=np.full(D, 0.07),
        profile=profile,
        state=state or PlantState(),
        limits=limits or Limits(),
        seed=seed,
    )


def with_belief(inp: DecisionInputs, belief: np.ndarray) -> DecisionInputs:
    return DecisionInputs(**{**inp.__dict__, "belief": belief})


def rank(inp: DecisionInputs) -> float:
    ev = evaluate(inp)
    if ev.choice is None:
        return restrictiveness(ActionKind.NO_SAFE_OPTION_ESCALATE, 0.0)
    a, q = CANDIDATES[ev.choice]
    return restrictiveness(a, q)


# ---------------------------------------------------------------- structure
@pytest.mark.req("MK-L4-001")
def test_candidate_grid() -> None:
    assert CANDIDATES[0] == (ActionKind.GO, 1.0)
    assert CANDIDATES[-1] == (ActionKind.PARK, 0.0)
    derates = [q for a, q in CANDIDATES if a == ActionKind.DERATE]
    assert derates == [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]


@pytest.mark.req("MK-L4-002")
@pytest.mark.req("MK-L4-003")
@settings(max_examples=20, deadline=None)
@given(st.floats(0.0, 0.5), st.floats(0.0, 0.5))
def test_choice_is_most_permissive_feasible(p_dev: float, p_at: float) -> None:
    inp = make_inputs(p_dev, p_at)
    ev = evaluate(inp)
    lim = inp.limits
    feas = (ev.p_foul <= lim.fouling_risk_budget + 1e-12) & (
        ev.p_water <= lim.water_risk_budget + 1e-12
    )
    if ev.choice is None:
        assert not feas.any()
    else:
        assert feas[ev.choice]
        assert not feas[: ev.choice].any()
    adv = decide(inp)
    if adv.action not in (ActionKind.GO, ActionKind.NO_SAFE_OPTION_ESCALATE):
        assert adv.binding_constraint


@pytest.mark.req("MK-L4-004")
def test_no_safe_option_when_every_candidate_breaches() -> None:
    inp = make_inputs(
        p_dev=0.0, p_at=0.95, state=PlantState(storage_hours=2.0, fouling_index=0.8), spread=0.0
    )
    adv = decide(inp)
    assert adv.action == ActionKind.NO_SAFE_OPTION_ESCALATE
    assert adv.reasons and "No candidate" in adv.reasons[0]
    assert "escalate" in adv.text.what.lower()


@pytest.mark.req("MK-L4-005")
def test_advisory_reports_breach_time_to_limit_evidence_and_assumptions() -> None:
    adv = decide(make_inputs(p_dev=0.1, p_at=0.6, spread=0.1))
    assert 0 <= adv.p_breach_full_scale <= 1
    assert adv.p_breach_full_scale == pytest.approx(adv.explanation.candidates[0].p_fouling_breach)
    assert adv.time_to_limit_hours is None or 0 < adv.time_to_limit_hours <= 72
    assert adv.evidence_level.value == "L0" and adv.assumption_share == 1.0
    names = [c.name for c in adv.constraints]
    assert names == ["fouling", "water_security", "dwell"]


# ---------------------------------------------------------------- safety properties
@pytest.mark.req("MK-L4-006")
@settings(max_examples=25, deadline=None)
@given(st.floats(0.0, 0.4), st.floats(0.0, 0.4), st.floats(0.0, 1.0), st.floats(0.0, 1.0))
def test_higher_bloom_probability_never_more_permissive(
    p_dev: float, p_at: float, f1: float, f2: float
) -> None:
    inp = make_inputs(p_dev, p_at)
    b = inp.belief.copy()
    # move mass from clear to developing and from developing to at_intake
    m1 = b[:, 0] * f1
    b2 = b.copy()
    b2[:, 0] -= m1
    b2[:, 1] += m1
    m2 = b2[:, 1] * f2
    b2[:, 1] -= m2
    b2[:, 2] += m2
    assert rank(with_belief(inp, b2)) >= rank(inp) - 1e-12


@pytest.mark.req("MK-L4-007")
@settings(max_examples=20, deadline=None)
@given(st.floats(0.0, 0.4), st.floats(0.0, 0.4), st.floats(1.0, 3.0))
def test_wider_spreads_never_more_permissive(p_dev: float, p_at: float, factor: float) -> None:
    inp = make_inputs(p_dev, p_at)
    wide = PROFILE.model_copy(
        update={
            "parameters": [
                p.model_copy(update={"rel_spread": p.rel_spread * factor})
                for p in PROFILE.parameters
            ]
        }
    )
    wider = DecisionInputs(**{**inp.__dict__, "profile": wide})
    assert rank(wider) >= rank(inp) - 1e-12
    ev0, ev1 = evaluate(inp), evaluate(wider)
    assert np.all(ev1.p_foul >= ev0.p_foul - 1e-12)
    assert np.all(ev1.p_water >= ev0.p_water - 1e-12)


@pytest.mark.req("MK-L4-008")
@settings(max_examples=20, deadline=None)
@given(st.floats(0.0, 0.4), st.floats(0.0, 0.4), st.floats(0.0, 1.0), st.floats(0.0, 1.0))
def test_tighter_budget_never_more_permissive(
    p_dev: float, p_at: float, s1: float, s2: float
) -> None:
    loose = Limits(fouling_risk_budget=0.1, water_risk_budget=0.1)
    tight = Limits(fouling_risk_budget=0.1 * s1, water_risk_budget=0.1 * s2)
    a = make_inputs(p_dev, p_at, limits=loose)
    b = make_inputs(p_dev, p_at, limits=tight)
    assert rank(b) >= rank(a) - 1e-12


@pytest.mark.req("MK-L4-009")
@settings(max_examples=20, deadline=None)
@given(st.floats(0.0, 0.4), st.floats(0.0, 0.4), st.floats(0.0, 36.0), st.floats(0.0, 36.0))
def test_lower_storage_never_loosens_water_constraint(
    p_dev: float, p_at: float, s1: float, s2: float
) -> None:
    lo, hi = sorted((s1, s2))
    a = evaluate(make_inputs(p_dev, p_at, state=PlantState(storage_hours=hi)))
    b = evaluate(make_inputs(p_dev, p_at, state=PlantState(storage_hours=lo)))
    assert np.all(b.p_water >= a.p_water - 1e-12)


@pytest.mark.req("MK-L4-010")
@settings(max_examples=20, deadline=None)
@given(
    st.sampled_from(list(range(len(CANDIDATES)))),
    st.floats(0.0, 11.9),
    st.floats(0.0, 0.3),
    st.floats(0.0, 0.3),
)
def test_dwell_blocks_relaxation(cur_idx: int, hours: float, p_dev: float, p_at: float) -> None:
    a, q = CANDIDATES[cur_idx]
    state = PlantState(current_action=a, current_scale=q, hours_in_action=hours)
    adv = decide(make_inputs(p_dev, p_at, state=state))
    assert restrictiveness(adv.action, adv.scale) >= restrictiveness(a, q) - 1e-12


@pytest.mark.req("MK-L4-010")
def test_escalation_is_immediate_within_dwell() -> None:
    state = PlantState(current_action=ActionKind.GO, current_scale=1.0, hours_in_action=1.0)
    adv = decide(make_inputs(p_dev=0.1, p_at=0.9, state=state, spread=0.05))
    assert restrictiveness(adv.action, adv.scale) > restrictiveness(ActionKind.GO, 1.0)


@pytest.mark.req("MK-L4-010")
def test_relaxation_after_dwell_needs_margin() -> None:
    state = PlantState(current_action=ActionKind.DERATE, current_scale=0.5, hours_in_action=48.0)
    ev = evaluate(make_inputs(p_dev=0.01, p_at=0.005, state=state))
    assert ev.choice is not None
    a, q = CANDIDATES[ev.choice]
    if restrictiveness(a, q) < restrictiveness(ActionKind.DERATE, 0.5):
        assert ev.p_foul[ev.choice] <= 0.8 * 0.05 + 1e-12


# ---------------------------------------------------------------- audit
@pytest.mark.req("MK-L4-011")
def test_advisory_reproducible_from_stored_inputs_and_seed() -> None:
    inp = make_inputs(0.05, 0.1)
    a = decide(inp)
    stored = json.loads(json.dumps(inp.to_json()))
    again = DecisionInputs.from_json(stored)
    b = decide(again)
    assert a == b
    assert a.inputs_hash == again.digest()
    assert a.id == a.inputs_hash[:16]
    c = decide(make_inputs(0.05, 0.1, seed=4))
    assert c.inputs_hash != a.inputs_hash


@pytest.mark.req("MK-L4-012")
def test_text_is_rendered_from_explanation() -> None:
    adv = decide(make_inputs(0.1, 0.3))
    ex = adv.explanation
    assert adv.text.what and adv.text.why and adv.text.change
    assert adv.text.change == ex.what_would_change[0]
    if ex.binding_constraint:
        assert ex.binding_constraint.replace("_", " ") in adv.text.why
    assert f"Evidence level {ex.evidence_level.value}" in adv.text.why
