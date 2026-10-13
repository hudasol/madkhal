"""Policies P0 to P5. Each is a pure function of its inputs (no hidden state, no I/O).

The risk table cache passed to the Madkhal policies is a memo of a pure function (the table
depends only on the day of year and the rounded plant state), so it does not change results.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

from madkhal.contract import ActionKind, InspectAssessment, Limits, PlantProfile, PlantState
from madkhal.decision import CANDIDATES, CostWeights, SurveyConfig, assess, evaluate, from_estimator
from madkhal.estimator import Draws
from madkhal.plant import PlantParams
from madkhal.plant import PlantState as SimState
from madkhal.plant import simulate as plant_simulate

from .advise import TableCache, issued_at

POLICIES = ("P0", "P1", "P2", "P3", "P4", "P5")
POLICY_NAMES = {
    "P0": "always_go",
    "P1": "alert_park",
    "P2": "seasonal_rule",
    "P3": "madkhal_no_inspect",
    "P4": "madkhal_inspect",
    "P5": "oracle",
}
ALERT_PARK_DAYS = 7
SEASONAL_SCALE = 0.7
SEASON_WINDOWS = (((8, 15), (10, 31)), ((1, 15), (3, 15)))
ORACLE_HORIZON_DAYS = 3


@dataclass(frozen=True)
class PolicyOutput:
    action: ActionKind
    scale: float
    escalated: bool = False


@dataclass(frozen=True)
class MadkhalContext:
    site: str
    draws: Draws
    profile: PlantProfile
    limits: Limits
    seed: int


# ---------------------------------------------------------------- simple rules
def always_go() -> PolicyOutput:
    return PolicyOutput(ActionKind.GO, 1.0)


def alert_park(alerts_so_far: np.ndarray, hold_days: int = ALERT_PARK_DAYS) -> PolicyOutput:
    """PARK while any alert happened in the last ``hold_days`` days (today included)."""
    recent = np.asarray(alerts_so_far, dtype=bool)[-hold_days:]
    if recent.any():
        return PolicyOutput(ActionKind.PARK, 0.0)
    return PolicyOutput(ActionKind.GO, 1.0)


def in_season(day: dt.date) -> bool:
    for (m0, d0), (m1, d1) in SEASON_WINDOWS:
        if (m0, d0) <= (day.month, day.day) <= (m1, d1):
            return True
    return False


def seasonal_rule(day: dt.date) -> PolicyOutput:
    if in_season(day):
        return PolicyOutput(ActionKind.DERATE, SEASONAL_SCALE)
    return PolicyOutput(ActionKind.GO, 1.0)


# ---------------------------------------------------------------- Madkhal
def _inputs(ctx: MadkhalContext, day: dt.date, doy: int, belief5: np.ndarray, state: PlantState):  # type: ignore[no-untyped-def]
    return from_estimator(
        ctx.site,
        issued_at(day),
        belief5,
        ctx.draws,
        doy,
        ctx.profile,
        state,
        ctx.limits,
        seed=ctx.seed,
    )


def least_bad(p_foul: np.ndarray, p_water: np.ndarray, limits: Limits) -> int:
    score = np.maximum(p_foul / limits.fouling_risk_budget, p_water / limits.water_risk_budget)
    return int(np.argmin(score))


def madkhal(
    ctx: MadkhalContext,
    day: dt.date,
    doy: int,
    belief5: np.ndarray,
    state: PlantState,
    cache: TableCache,
) -> PolicyOutput:
    """P3: the decision engine on the current belief."""
    inp = _inputs(ctx, day, doy, belief5, state)
    ev = evaluate(inp, cache.get(inp, doy))
    if ev.choice is None:
        a, q = CANDIDATES[least_bad(ev.p_foul, ev.p_water, ctx.limits)]
        return PolicyOutput(a, q, escalated=True)
    a, q = CANDIDATES[ev.choice]
    return PolicyOutput(a, q)


def inspect_request(
    ctx: MadkhalContext,
    day: dt.date,
    doy: int,
    belief5: np.ndarray,
    state: PlantState,
    cache: TableCache,
    survey: SurveyConfig,
    weights: CostWeights,
) -> InspectAssessment:
    """P4, first step: is a survey worth its cost on this belief?"""
    inp = _inputs(ctx, day, doy, belief5, state)
    return assess(inp, cache.get(inp, doy), survey, weights)


# ---------------------------------------------------------------- oracle
def oracle(
    params: PlantParams,
    state: SimState,
    future_load: np.ndarray,
    weights: CostWeights,
) -> np.ndarray:
    """P5: per lane, the candidate with the lowest weighted cost over the next 72 hours given
    the true future loads (N, 72) and the true plant. Returns the scale per lane."""
    n = state.fouling.size
    k_n = len(CANDIDATES)
    idx = np.repeat(np.arange(n), k_n)
    st = state.take(idx)
    pp = params.take(idx)
    q = np.tile(np.array([c[1] for c in CANDIDATES]), n)
    load = future_load[idx]
    before = {
        k: getattr(st, k).copy()
        for k in ("forced_shutdowns", "cleanings", "unserved", "wear", "restarts")
    }
    plant_simulate(pp, load, q, st, "full")
    derate = np.tile(np.array([1.0 if a == ActionKind.DERATE else 0.0 for a, _ in CANDIDATES]), n)
    cost = (
        (st.forced_shutdowns - before["forced_shutdowns"]) * weights.forced_shutdown
        + (st.cleanings - before["cleanings"]) * weights.cleaning
        + (st.unserved - before["unserved"]) * weights.unserved_m3
        + (st.wear - before["wear"]) * weights.membrane_index
        + (st.restarts - before["restarts"]) * weights.restart
        + derate * weights.derate_day * ORACLE_HORIZON_DAYS
    ).reshape(n, k_n)
    # ties go to the most permissive candidate (more water produced)
    best = np.argmin(cost + np.arange(k_n)[None, :] * 1e-9, axis=1)
    out: np.ndarray = np.array([c[1] for c in CANDIDATES])[best]
    return out
