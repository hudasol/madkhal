"""Stylised SWRO unit plant, hourly steps, vectorised over lanes (samples, seeds, candidates).

Quantities (hypothetical plant, synthetic parameters):

* Intake load index L (relative to a pretreatment design load of 1.0): background load plus a
  bloom load while the bloom is at the intake. The bloom load is Pareto distributed (heavy
  tail) with a lower bound ``bloom_load_min`` and tail index ``bloom_tail_alpha``.
* Flow scale q in [0, 1] set by the action; the load sent to pretreatment is L * q.
* Pretreatment capacity C, raised by the coagulant boost when derating (0 < q < 1).
  Breakthrough B = max(0, L q - C).
* Fouling index F grows by k_fouling * B per hour and only falls through a cleaning.
  F >= 1 is the hard limit: forced shutdown, cleaning, restart penalty.
* Product storage S (m3) fills with production and drains with demand. When it is empty,
  demand that cannot be met accrues as unserved water.

Two modes share one step function:

* ``decision``: used inside the decision horizon. After a breach the lane stays offline for
  the rest of the horizon. This is conservative and makes breach and unserved water monotone
  in every adverse parameter (an earlier breach is never better for water security).
* ``full``: used by the lab over years: forced cleaning, restart after a stop, planned
  cleaning at day boundaries.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace

import numpy as np

from madkhal.contract import Parameter, PlantProfile

INF_HOURS = 1e9


@dataclass(frozen=True)
class PlantParams:
    """Parameter values per lane, each an array of shape (N,)."""

    design_flow: np.ndarray
    demand_fraction: np.ndarray
    storage_capacity_h: np.ndarray
    background_load: np.ndarray
    bloom_load_min: np.ndarray
    bloom_tail_alpha: np.ndarray
    pretreat_capacity: np.ndarray
    coagulant_boost: np.ndarray
    k_fouling: np.ndarray
    fouling_after_clean: np.ndarray
    clean_hours: np.ndarray
    restart_hours: np.ndarray
    planned_clean_at: np.ndarray
    planned_clean_hours: np.ndarray
    wear_per_clean: np.ndarray
    wear_per_breakthrough: np.ndarray

    @property
    def n(self) -> int:
        return int(self.design_flow.size)

    @property
    def demand(self) -> np.ndarray:
        out: np.ndarray = self.design_flow * self.demand_fraction
        return out

    @property
    def storage_capacity(self) -> np.ndarray:
        out: np.ndarray = self.storage_capacity_h * self.demand
        return out

    def take(self, idx: np.ndarray) -> PlantParams:
        return PlantParams(**{k: getattr(self, k)[idx] for k in _FIELDS})

    def bloom_load(self, u: np.ndarray) -> np.ndarray:
        """Pareto bloom load for uniforms u in (0, 1]. Monotone: larger for a larger lower
        bound or a smaller tail index, for every u."""
        uu = np.clip(u, 1e-12, 1.0)
        out: np.ndarray = self.bloom_load_min * uu ** (-1.0 / self.bloom_tail_alpha)
        return out


_FIELDS = tuple(PlantParams.__dataclass_fields__)
_KEY = {f: f"plant.{f}" for f in _FIELDS}
_KEY["design_flow"] = "plant.design_flow_m3h"
_KEY["k_fouling"] = "plant.k_fouling"


def _value(p: Parameter, z: np.ndarray | None, mode: str, scale: float) -> np.ndarray:
    n = 1 if z is None else z.size
    base = np.full(n, p.value, dtype=float)
    if z is None or mode == "nominal":
        return base
    sigma = p.rel_spread * scale
    if mode == "adverse":
        if p.role == "operating":
            return base
        sign = 1.0 if p.adverse == "up" else -1.0
        out: np.ndarray = base * np.exp(sign * sigma * np.maximum(z, 0.0))
        return out
    if mode == "two_sided":
        out2: np.ndarray = base * np.exp(sigma * z)
        return out2
    raise ValueError(f"unknown sampling mode {mode}")


def sample_params(
    profile: PlantProfile,
    n: int,
    rng: np.random.Generator | None = None,
    mode: str = "adverse",
    spread_scale: float = 1.0,
    z: dict[str, np.ndarray] | None = None,
) -> PlantParams:
    """Parameter lanes from a profile.

    ``adverse``: each physics parameter moves only towards its adverse side, by max(z, 0)
    times its spread, and stays nominal otherwise; operating quantities stay at their value.
    A wider spread can therefore only make every lane worse (ADR 0007). ``two_sided``: lognormal
    around the nominal value (used for hidden truth plants in the lab). ``nominal``: no spread.
    Pass ``z`` (standard normals per key) to reuse common random numbers.
    """
    values: dict[str, np.ndarray] = {}
    for f in _FIELDS:
        p = profile.param(_KEY[f])
        if mode == "nominal":
            zz = None
        elif z is not None:
            zz = z[_KEY[f]]
        else:
            if rng is None:
                raise ValueError("rng or z is required unless mode is nominal")
            zz = rng.standard_normal(n)
        v = _value(p, zz, mode, spread_scale)
        values[f] = np.broadcast_to(v, (n,)).astype(float).copy()
    out = PlantParams(**values)
    return replace(out, demand_fraction=np.clip(out.demand_fraction, 0.05, 1.0))


def standard_normals(n: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    return {_KEY[f]: rng.standard_normal(n) for f in _FIELDS}


@dataclass
class PlantState:
    """Mutable state per lane."""

    fouling: np.ndarray
    storage: np.ndarray  # m3
    offline: np.ndarray  # hours left offline (cleaning or restart)
    parked: np.ndarray  # bool: stopped by PARK, a restart is needed before producing
    # accumulators
    produced: np.ndarray = field(default_factory=lambda: np.zeros(0))
    delivered: np.ndarray = field(default_factory=lambda: np.zeros(0))
    unserved: np.ndarray = field(default_factory=lambda: np.zeros(0))
    curtailed: np.ndarray = field(default_factory=lambda: np.zeros(0))
    load_in: np.ndarray = field(default_factory=lambda: np.zeros(0))
    load_removed: np.ndarray = field(default_factory=lambda: np.zeros(0))
    breakthrough: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fouling_dose: np.ndarray = field(default_factory=lambda: np.zeros(0))
    forced_shutdowns: np.ndarray = field(default_factory=lambda: np.zeros(0))
    cleanings: np.ndarray = field(default_factory=lambda: np.zeros(0))
    restarts: np.ndarray = field(default_factory=lambda: np.zeros(0))
    wear: np.ndarray = field(default_factory=lambda: np.zeros(0))
    breach_hour: np.ndarray = field(default_factory=lambda: np.zeros(0))
    first_unserved_hour: np.ndarray = field(default_factory=lambda: np.zeros(0))
    hours: int = 0

    @staticmethod
    def initial(
        n: int,
        params: PlantParams,
        fouling: float | np.ndarray = 0.2,
        storage_hours: float | np.ndarray = 24.0,
    ) -> PlantState:
        z = np.zeros(n)
        storage = np.minimum(
            np.broadcast_to(storage_hours, (n,)) * params.demand, params.storage_capacity
        )
        return PlantState(
            fouling=np.broadcast_to(np.asarray(fouling, float), (n,)).copy(),
            storage=storage.astype(float).copy(),
            offline=z.copy(),
            parked=np.zeros(n, dtype=bool),
            produced=z.copy(),
            delivered=z.copy(),
            unserved=z.copy(),
            curtailed=z.copy(),
            load_in=z.copy(),
            load_removed=z.copy(),
            breakthrough=z.copy(),
            fouling_dose=z.copy(),
            forced_shutdowns=z.copy(),
            cleanings=z.copy(),
            restarts=z.copy(),
            wear=z.copy(),
            breach_hour=np.full(n, np.inf),
            first_unserved_hour=np.full(n, np.inf),
        )

    def copy(self) -> PlantState:
        return copy.deepcopy(self)


def step(
    st: PlantState,
    params: PlantParams,
    load: np.ndarray,
    q: np.ndarray,
    mode: str = "full",
) -> None:
    """Advance every lane by one hour in place. ``load`` and ``q`` have shape (N,)."""
    qq = np.clip(np.asarray(q, float), 0.0, 1.0)
    want_run = qq > 0.0
    # a PARK stops the plant; leaving PARK needs a restart
    newly_parked = (~want_run) & (~st.parked)
    st.parked = st.parked | newly_parked
    restarting = want_run & st.parked & (st.offline <= 0.0)
    st.offline = np.where(restarting, params.restart_hours, st.offline)
    st.restarts = st.restarts + restarting
    st.parked = np.where(restarting, False, st.parked)
    online = want_run & (st.offline <= 0.0) & ~st.parked
    boost = np.where((qq > 0.0) & (qq < 1.0), params.coagulant_boost, 0.0)
    cap = params.pretreat_capacity * (1.0 + boost)
    sent = np.where(online, load * qq, 0.0)
    b = np.maximum(sent - cap, 0.0)
    st.load_in = st.load_in + sent
    st.load_removed = st.load_removed + (sent - b)
    st.breakthrough = st.breakthrough + b
    df = params.k_fouling * b
    st.fouling = st.fouling + df
    st.fouling_dose = st.fouling_dose + df
    st.wear = st.wear + params.wear_per_breakthrough * b
    prod = np.where(online, qq * params.design_flow, 0.0)
    breach = online & (st.fouling >= 1.0)
    first = breach & ~np.isfinite(st.breach_hour)
    st.breach_hour = np.where(first, float(st.hours), st.breach_hour)
    if np.any(breach):
        st.forced_shutdowns = st.forced_shutdowns + breach
        if mode == "decision":
            st.offline = np.where(breach, INF_HOURS, st.offline)
        else:
            st.cleanings = st.cleanings + breach
            st.wear = st.wear + breach * 2.0 * params.wear_per_clean
            st.fouling = np.where(breach, params.fouling_after_clean, st.fouling)
            st.offline = np.where(breach, params.clean_hours + params.restart_hours, st.offline)
            st.restarts = st.restarts + breach
    # the hour's production counts unless the plant tripped during it
    prod = np.where(breach, 0.0, prod)
    # offline counters tick down for lanes that did not run this hour
    st.offline = np.where(online | breach, st.offline, np.maximum(st.offline - 1.0, 0.0))
    demand = params.demand
    avail = st.storage + prod
    deliver = np.minimum(demand, avail)
    short = demand - deliver
    st.unserved = st.unserved + short
    first_short = (short > 1e-9) & ~np.isfinite(st.first_unserved_hour)
    st.first_unserved_hour = np.where(first_short, float(st.hours), st.first_unserved_hour)
    after = avail - deliver
    cap_s = params.storage_capacity
    spill = np.maximum(after - cap_s, 0.0)
    st.curtailed = st.curtailed + spill
    st.storage = after - spill
    st.produced = st.produced + prod
    st.delivered = st.delivered + deliver
    st.hours += 1


def planned_cleaning(st: PlantState, params: PlantParams) -> np.ndarray:
    """Start a planned cleaning where fouling reached the planned threshold (lab only)."""
    due = (st.fouling >= params.planned_clean_at) & (st.offline <= 0.0)
    st.cleanings = st.cleanings + due
    st.wear = st.wear + due * params.wear_per_clean
    st.fouling = np.where(due, params.fouling_after_clean, st.fouling)
    st.offline = np.where(due, params.planned_clean_hours + params.restart_hours, st.offline)
    st.restarts = st.restarts + due
    out: np.ndarray = due
    return out


def simulate(
    params: PlantParams,
    load: np.ndarray,
    q: np.ndarray,
    st: PlantState,
    mode: str = "full",
) -> PlantState:
    """Run ``load.shape[1]`` hours. ``load`` is (N, H); ``q`` is (N,) or (N, H)."""
    n, h = load.shape
    qa = np.asarray(q, float)
    for t in range(h):
        qt = qa if qa.ndim == 1 else qa[:, t]
        step(st, params, load[:, t], qt, mode)
    return st
