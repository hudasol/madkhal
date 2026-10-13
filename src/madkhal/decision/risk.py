"""Risk table: plant outcomes per draw, start state and candidate action over the horizon.

For every posterior draw d, every start state s (clear, developing, at_intake) and every
candidate k, one bloom path and one plant are simulated with common random numbers (the same
bloom uniforms, bloom load and plant parameters for all s and k of a draw). The table is then
made monotone across start states: a more severe start state is never safer than a less severe
one (a cumulative maximum, which can only raise risk). Every probability the decision uses is a
belief weighted average of this table, hence linear in the belief.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from madkhal.contract import ActionKind
from madkhal.core.determinism import substream
from madkhal.plant import PlantState, sample_params, simulate, standard_normals

from .inputs import DecisionInputs

CANDIDATES: tuple[tuple[ActionKind, float], ...] = (
    (ActionKind.GO, 1.0),
    *((ActionKind.DERATE, round(q, 1)) for q in (0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2)),
    (ActionKind.PARK, 0.0),
)
N_STATES = 3


@dataclass(frozen=True)
class RiskTable:
    """Arrays of shape (D, 3, K)."""

    fouling_breach: np.ndarray  # bool as float
    water_breach: np.ndarray  # bool as float
    unserved_m3: np.ndarray
    breach_hour: np.ndarray  # inf when no breach

    def weighted(self, belief: np.ndarray, what: str) -> np.ndarray:
        """Belief weighted mean over draws and start states, one value per candidate."""
        arr = getattr(self, what)
        out: np.ndarray = np.einsum("ds,dsk->k", belief, arr) / belief.shape[0]
        return out


def bloom_paths(inp: DecisionInputs, rng: np.random.Generator) -> np.ndarray:
    """Daily at_intake indicator, shape (D, 3, days), one path per draw and start state.

    The same uniforms drive every start state of a draw (common random numbers)."""
    d_n, days = inp.n_draws, inp.horizon_days
    v = rng.random((d_n, days))
    at = np.zeros((d_n, N_STATES, days), dtype=bool)
    for s in range(N_STATES):
        state = np.full(d_n, s)
        for k in range(days):
            if k > 0:
                lam = inp.hazard[:, k]
                u = v[:, k]
                from_clear = np.where(u < lam, 1, 0)
                from_dev = np.where(u < inp.p_da, 2, np.where(u > 1.0 - inp.p_dc, 0, 1))
                from_at = np.where(u > 1.0 - inp.p_ac, 0, 2)
                state = np.where(state == 0, from_clear, np.where(state == 1, from_dev, from_at))
            at[:, s, k] = state == 2
    return at


def risk_table(inp: DecisionInputs, spread_scale: float = 1.0) -> RiskTable:
    rng = substream(inp.seed, f"decision.{inp.site}")
    d_n, k_n, h = inp.n_draws, len(CANDIDATES), inp.limits.horizon_hours
    at = bloom_paths(inp, rng)  # (D, 3, days)
    u_load = rng.random(d_n)
    z = standard_normals(d_n, rng)
    params_d = sample_params(inp.profile, d_n, mode="adverse", z=z, spread_scale=spread_scale)
    bloom = params_d.bloom_load(u_load)  # (D,)
    # lanes ordered (d, s, k)
    lane_d = np.repeat(np.arange(d_n), N_STATES * k_n)
    lane_s = np.tile(np.repeat(np.arange(N_STATES), k_n), d_n)
    lane_k = np.tile(np.arange(k_n), d_n * N_STATES)
    params = params_d.take(lane_d)
    hours = np.arange(h)
    day_of_hour = hours // 24
    at_hourly = at[lane_d, lane_s][:, day_of_hour]  # (N, H)
    load = params.background_load[:, None] + at_hourly * bloom[lane_d][:, None]
    q = np.array([c[1] for c in CANDIDATES])[lane_k]
    st = PlantState.initial(len(lane_d), params, inp.state.fouling_index, inp.state.storage_hours)
    if inp.state.current_action == ActionKind.PARK:
        st.parked[:] = True
    st = simulate(params, load, q, st, mode="decision")
    shape = (d_n, N_STATES, k_n)
    foul = np.isfinite(st.breach_hour).reshape(shape).astype(float)
    unserved = st.unserved.reshape(shape)
    water = (unserved > inp.limits.water_allowance_m3 + 1e-9).astype(float)
    bh = st.breach_hour.reshape(shape)
    # monotone across start states: clear <= developing <= at_intake
    foul = np.maximum.accumulate(foul, axis=1)
    water = np.maximum.accumulate(water, axis=1)
    unserved = np.maximum.accumulate(unserved, axis=1)
    bh = np.minimum.accumulate(bh, axis=1)
    return RiskTable(fouling_breach=foul, water_breach=water, unserved_m3=unserved, breach_hour=bh)


def time_to_limit(
    table: RiskTable, belief: np.ndarray, k: int, quantile: float = 0.05
) -> float | None:
    """Earliest hour by which P(breach) reaches ``quantile`` for candidate k (the 95 percent
    risk quantile of the time to limit), or None if it stays below within the horizon."""
    bh = table.breach_hour[:, :, k]  # (D, 3)
    w = belief / belief.shape[0]
    finite = np.isfinite(bh)
    if not finite.any():
        return None
    times = np.sort(np.unique(bh[finite]))
    for t in times:
        if float(np.sum(w * (bh <= t))) >= quantile:
            return float(t) + 1.0
    return None
