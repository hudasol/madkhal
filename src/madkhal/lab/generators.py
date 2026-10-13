"""Scenario generators for the policy lab. SYNTHETIC worlds, not data.

G1 is the estimator's own model at posterior means (calibrated to Nadhir's numbers through the
priors), so it shares the estimator's assumptions and flatters it. G2 breaks those assumptions
on purpose. Both are written by the same author as the method (docs/PREREGISTRATION.md).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np

from madkhal.core.determinism import substream
from madkhal.estimator import AT_I, AT_V, DEV_I, DEV_V, Draws, draw_parameters, sample_states
from madkhal.plant import PlantParams, default_profile, sample_params

from .inputs import monthly_clear_prob, prior_spec

START = dt.date(2021, 1, 1)
DAYS = 730
SITE = "kalba"

# G2 structural changes (docs/PREREGISTRATION.md)
G2_TAIL_FACTOR = 0.6
G2_MISS_AFTER_MISS = 0.8
G2_SUMMER_CLEAR_FACTOR = 0.4
G2_SUMMER_MONTHS = (6, 7, 8, 9)
G2_SPECIES_RATE = 0.5
G2_FA_START_FACTOR = 1.0 / 3.0
G2_FA_CONTINUE = 0.7


@dataclass(frozen=True)
class World:
    """One synthetic run: truth, observations and the hidden truth plant (one lane)."""

    generator: str
    seed: int
    dates: tuple[dt.date, ...]
    doy: np.ndarray
    developing: np.ndarray  # bool (T,)
    at_intake: np.ndarray  # bool (T,)
    visible: np.ndarray  # bool (T,): in a bloom the broadband detector can see
    clear: np.ndarray  # bool (T,)
    alert: np.ndarray  # bool (T,)
    bloom_load: np.ndarray  # (T,) load added while at the intake, else 0
    plant: PlantParams  # one lane, physics drawn two sided
    survey_fly_u: np.ndarray  # (T,) uniforms for weather availability
    survey_det_u: np.ndarray  # (T,) uniforms for survey detection

    @property
    def days(self) -> int:
        return int(self.doy.size)

    def at_within(self, h: int) -> np.ndarray:
        a = self.at_intake.astype(bool)
        out = a.copy()
        for k in range(1, h + 1):
            out[:-k] |= a[k:]
        return out

    def truth_state3(self) -> np.ndarray:
        """0 clear, 1 developing, 2 at the intake."""
        out: np.ndarray = np.where(self.at_intake, 2, np.where(self.developing, 1, 0))
        return out


@lru_cache(maxsize=4)
def truth_detector(site: str = SITE) -> Draws:
    """Posterior means of the estimator's parameters: the truth of generator G1."""
    return draw_parameters(prior_spec(site), 4000, 7).posterior_mean()


def _calendar(days: int) -> tuple[tuple[dt.date, ...], np.ndarray, np.ndarray]:
    dates = tuple(START + dt.timedelta(days=k) for k in range(days))
    doy = np.array([d.timetuple().tm_yday for d in dates])
    month = np.array([d.month for d in dates])
    return dates, doy, month


def _episode_loads(
    at: np.ndarray, plant: PlantParams, u: np.ndarray, tail_factor: float = 1.0
) -> np.ndarray:
    """One Pareto load per continuous run of days at the intake."""
    load = np.zeros(at.size)
    k = 0
    t = 0
    while t < at.size:
        if at[t]:
            s = t
            while t < at.size and at[t]:
                t += 1
            alpha = float(plant.bloom_tail_alpha[0]) * tail_factor
            lo = float(plant.bloom_load_min[0])
            load[s:t] = lo * max(float(u[k % u.size]), 1e-12) ** (-1.0 / alpha)
            k += 1
        else:
            t += 1
    return load


def truth_plant(seed: int, mult: dict[str, float] | None = None) -> PlantParams:
    """Hidden truth plant for a seed: physics two sided, operating quantities at their value.
    ``mult`` multiplies named parameters (sensitivity runs)."""
    prof = default_profile()
    rng = substream(seed, "lab.truthplant")
    z = {
        p.key: (np.zeros(1) if p.role == "operating" else rng.standard_normal(1))
        for p in prof.parameters
    }
    out = sample_params(prof, 1, mode="two_sided", z=z)
    for key, m in (mult or {}).items():
        field = key.removeprefix("plant.")
        field = {"design_flow_m3h": "design_flow"}.get(field, field)
        out = replace(out, **{field: getattr(out, field) * m})
    return out


DETECTOR_KEYS = ("alpha", "visible_share", "beta_at")


def scaled_detector(tr: Draws, mult: dict[str, float] | None) -> Draws:
    if not mult:
        return tr
    for key in mult:
        if key not in DETECTOR_KEYS:
            raise KeyError(key)

    def sc(key: str, arr: np.ndarray, factor_key: str | None = None) -> np.ndarray:
        m = mult.get(factor_key or key, 1.0) if mult else 1.0
        out: np.ndarray = np.clip(arr * m, 1e-6, 0.999)
        return out

    return replace(
        tr,
        alpha=sc("alpha", tr.alpha),
        visible_share=sc("visible_share", tr.visible_share),
        beta_at=sc("beta_at", tr.beta_at),
        beta_dev=sc("beta_dev", tr.beta_dev, "beta_at"),
    )


def g1(
    seed: int,
    days: int = DAYS,
    site: str = SITE,
    plant_mult: dict[str, float] | None = None,
    detector_mult: dict[str, float] | None = None,
) -> World:
    rng = substream(seed, "lab.G1.world")
    dates, doy, month = _calendar(days)
    tr = scaled_detector(truth_detector(site), detector_mult)
    states = sample_states(doy, tr, rng)
    cp = monthly_clear_prob(site)[month - 1]
    clear = rng.random(days) < cp
    lik = np.array(
        [
            float(tr.alpha[0]),
            float(tr.beta_dev[0]),
            float(tr.alpha[0]),
            float(tr.beta_at[0]),
            float(tr.alpha[0]),
        ]
    )
    alert = clear & (rng.random(days) < lik[states])
    plant = truth_plant(seed, plant_mult)
    at = (states == AT_V) | (states == AT_I)
    dev = (states == DEV_V) | (states == DEV_I)
    vis = (states == DEV_V) | (states == AT_V)
    loads = _episode_loads(at, plant, rng.random(64))
    s_rng = substream(seed, "lab.survey")
    return World(
        "G1",
        seed,
        dates,
        doy,
        dev,
        at,
        vis,
        clear,
        alert,
        loads,
        plant,
        s_rng.random(days),
        s_rng.random(days),
    )


def g2(seed: int, days: int = DAYS, site: str = SITE) -> World:
    rng = substream(seed, "lab.G2.world")
    dates, doy, month = _calendar(days)
    tr = truth_detector(site)
    states = sample_states(doy, tr, rng)
    # extra species events: a second chain whose blooms are never visible to the satellite
    species = replace(tr, onset_rate=np.array([G2_SPECIES_RATE]), visible_share=np.array([0.0]))
    extra = sample_states(doy, species, rng)
    at = (states == AT_V) | (states == AT_I) | (extra == AT_I) | (extra == AT_V)
    dev = ((states == DEV_V) | (states == DEV_I) | (extra == DEV_I) | (extra == DEV_V)) & ~at
    vis = (states == DEV_V) | (states == AT_V)
    cp = monthly_clear_prob(site)[month - 1].copy()
    summer = np.isin(month, G2_SUMMER_MONTHS)
    cp[summer] *= G2_SUMMER_CLEAR_FACTOR
    clear = rng.random(days) < cp
    alpha = float(tr.alpha[0])
    b_dev, b_at = float(tr.beta_dev[0]), float(tr.beta_at[0])
    alert = np.zeros(days, dtype=bool)
    in_fa = False
    missed = False
    u = rng.random(days)
    for t in range(days):
        if not vis[t]:
            missed = False
        if not clear[t]:
            continue
        if vis[t]:
            p = b_at if states[t] == AT_V else b_dev
            if missed:
                p = min(p, 1.0 - G2_MISS_AFTER_MISS)
            alert[t] = u[t] < p
            missed = not alert[t]
            in_fa = False
            continue
        # clustered false alarms with a marginal rate near alpha
        if in_fa:
            alert[t] = u[t] < G2_FA_CONTINUE
            in_fa = bool(alert[t])
        else:
            alert[t] = u[t] < alpha * G2_FA_START_FACTOR
            in_fa = bool(alert[t])
    plant = truth_plant(seed)
    loads = _episode_loads(at, plant, rng.random(64), G2_TAIL_FACTOR)
    s_rng = substream(seed, "lab.survey")
    return World(
        "G2",
        seed,
        dates,
        doy,
        dev,
        at,
        vis,
        clear,
        alert,
        loads,
        plant,
        s_rng.random(days),
        s_rng.random(days),
    )


GENERATORS = {"G1": g1, "G2": g2}


def world(generator: str, seed: int, days: int = DAYS) -> World:
    return GENERATORS[generator](seed, days)
