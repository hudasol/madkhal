"""One at a time sensitivity of plant risk to each parameter ("measure this first").

Method ported from Dhill (src/dhill/sensitivity.py at b751f00): move one parameter by plus and
minus one prior spread (lognormal) while the others stay nominal, and record the swing of two
risk measures over a 72 hour horizon:

* fouling: P(fouling limit reached | bloom at the intake from hour 0), at full scale and at a
  derate of 0.6 with the coagulant boost (the larger swing counts);
* water: hours at a derate of 0.5, from the default storage level, before unserved water
  begins (as a share of the horizon).

Interactions are not captured; the ranking is a guide to which measurement would shrink
decision uncertainty most, not a variance decomposition.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from madkhal.contract import PlantProfile
from madkhal.core.determinism import substream

from .model import PlantParams, PlantState, sample_params, simulate

HORIZON_H = 72
N_SAMPLES = 2000
FULL_SCALE = 1.0
DERATE_SCALE = 0.6
WATER_SCALE = 0.5


@dataclass(frozen=True)
class SensitivityRow:
    key: str
    label: str
    rel_spread: float
    swing_fouling: float
    swing_water: float
    score: float
    rank: int


def _first_breach(params: PlantParams, u: np.ndarray, q: float, f0: float, s0: float) -> float:
    n = u.size
    load = (params.background_load + params.bloom_load(u))[:, None] * np.ones((1, HORIZON_H))
    st = simulate(
        params, load, np.full(n, q), PlantState.initial(n, params, f0, s0), mode="decision"
    )
    return float(np.mean(np.isfinite(st.breach_hour)))


def _risks(params: PlantParams, u: np.ndarray, f0: float, s0: float) -> tuple[float, float, float]:
    n = u.size
    p_full = _first_breach(params, u, FULL_SCALE, f0, s0)
    p_derate = _first_breach(params, u, DERATE_SCALE, f0, s0)
    st = simulate(
        params,
        params.background_load[:, None] * np.ones((1, HORIZON_H)),
        np.full(n, WATER_SCALE),
        PlantState.initial(n, params, f0, s0),
        mode="decision",
    )
    t_water = float(np.mean(np.minimum(st.first_unserved_hour, HORIZON_H))) / HORIZON_H
    return p_full, p_derate, t_water


def tornado(
    profile: PlantProfile, seed: int = 11, fouling0: float = 0.2, storage_h: float = 24.0
) -> list[SensitivityRow]:
    u = substream(seed, "plant.sensitivity").random(N_SAMPLES)
    rows = []
    for p in profile.parameters:
        lanes = []
        for sign in (+1.0, -1.0):
            moved = profile.model_copy(
                update={
                    "parameters": [
                        q.model_copy(update={"value": q.value * float(np.exp(sign * q.rel_spread))})
                        if q.key == p.key
                        else q
                        for q in profile.parameters
                    ]
                }
            )
            params = sample_params(moved, N_SAMPLES, mode="nominal")
            lanes.append(_risks(params, u, fouling0, storage_h))
        (f_hi, d_hi, w_hi), (f_lo, d_lo, w_lo) = lanes
        sf = max(abs(f_hi - f_lo), abs(d_hi - d_lo))
        sw = abs(w_hi - w_lo)
        rows.append((p.key, p.label, p.rel_spread, sf, sw, max(sf, sw)))
    rows.sort(key=lambda r: (-r[5], r[0]))
    return [
        SensitivityRow(k, lab, rs, round(sf, 4), round(sw, 4), round(sc, 4), i + 1)
        for i, (k, lab, rs, sf, sw, sc) in enumerate(rows)
    ]
