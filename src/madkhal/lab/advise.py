"""Advisories over real evidence (replay) and over user scenarios (Scenario Lab).

REPLAY: real satellite evidence, hypothetical plant. The plant is held in a neutral state
(fouling 0.2, storage 24 hours of demand) because no real plant is modelled; only the action
in force is carried from day to day so that the dwell and hysteresis rules apply. No outcome
of any real plant is reported or implied.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

from madkhal.contract import (
    REPLAY_LABEL,
    ActionKind,
    Advisory,
    CoverageState,
    DetectorState,
    EvidenceDay,
    Limits,
    PlantProfile,
    PlantState,
    Scenario,
)
from madkhal.core.determinism import substream
from madkhal.decision import (
    CANDIDATES,
    DecisionInputs,
    decide,
    evaluate,
    from_estimator,
    risk_table,
)
from madkhal.decision.risk import RiskTable
from madkhal.estimator import BeliefSeries, Draws, belief_series, draw_parameters
from madkhal.plant import PlantState as SimState
from madkhal.plant import default_profile, planned_cleaning, sample_params, simulate

from .inputs import prior_spec
from .replay import belief_replay

DECISION_HOUR_UTC = 2  # 06:00 in Asia/Dubai


def issued_at(day: dt.date) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, DECISION_HOUR_UTC, tzinfo=dt.UTC)


@lru_cache(maxsize=8)
def _series(site: str, draws: int, seed: int) -> BeliefSeries:
    return belief_replay(site, draws, seed)


def advisory_for(
    site: str,
    day: dt.date,
    draws: int = 400,
    seed: int = 7,
    state: PlantState | None = None,
    limits: Limits | None = None,
    profile: PlantProfile | None = None,
) -> Advisory:
    """REPLAY advisory for one site and day (belief at the end of that day)."""
    bs = _series(site, draws, seed)
    i = bs.index_of(day)
    inp = from_estimator(
        site,
        issued_at(day),
        bs.result.posterior[i],
        bs.draws,
        day.timetuple().tm_yday,
        profile or default_profile(),
        state or PlantState(),
        limits or Limits(),
        seed=seed,
        label=REPLAY_LABEL,
    )
    return decide(inp)


@dataclass(frozen=True)
class DayAdvice:
    date: dt.date
    action: ActionKind
    scale: float
    p_fouling: float
    p_water: float
    p_breach_full: float
    binding: str | None
    dwell_held: bool


class TableCache:
    """A memo of ``risk_table``: tables keyed by every input that changes them.

    The belief is not part of the key because the table does not depend on it; the decision
    weights the table by the belief afterwards (ADR 0007). Safe to share across runs.
    """

    def __init__(self) -> None:
        self._t: dict[tuple[object, ...], RiskTable] = {}

    @staticmethod
    def _context(inp: DecisionInputs) -> str:
        """Content hash of everything except the day and the plant state (no object ids)."""
        h = hashlib.sha256()
        for a in (inp.p_da, inp.p_dc, inp.p_ac):
            h.update(np.ascontiguousarray(a, dtype=np.float64).tobytes())
        h.update(inp.profile.model_dump_json().encode())
        h.update(inp.limits.model_dump_json().encode())
        h.update(f"{inp.site}|{inp.seed}|{inp.n_draws}".encode())
        return h.hexdigest()

    def get(self, inp: DecisionInputs, doy: int) -> RiskTable:
        key = (
            self._context(inp),
            doy,
            inp.state.current_action == ActionKind.PARK,
            round(inp.state.fouling_index, 6),
            round(inp.state.storage_hours, 6),
        )
        if key not in self._t:
            self._t[key] = risk_table(inp)
        return self._t[key]


def advise_series(
    site: str,
    bs: BeliefSeries,
    start: int,
    end: int,
    seed: int = 7,
    limits: Limits | None = None,
    profile: PlantProfile | None = None,
    cache: TableCache | None = None,
) -> list[DayAdvice]:
    """Daily advice over days [start, end) of a belief series, carrying the action in force."""
    lim = limits or Limits()
    prof = profile or default_profile()
    tc = cache or TableCache()
    out: list[DayAdvice] = []
    cur_a, cur_q, hours = ActionKind.GO, 1.0, 1000.0
    for i in range(start, end):
        day = bs.dates[i]
        doy = day.timetuple().tm_yday
        state = PlantState(current_action=cur_a, current_scale=cur_q, hours_in_action=hours)
        inp = from_estimator(
            site, issued_at(day), bs.result.posterior[i], bs.draws, doy, prof, state, lim, seed=seed
        )
        ev = evaluate(inp, tc.get(inp, doy))
        if ev.choice is None:
            a, q = ActionKind.NO_SAFE_OPTION_ESCALATE, 0.0
            pf = float(np.min(ev.p_foul))
            pw = float(np.min(ev.p_water))
        else:
            a, q = CANDIDATES[ev.choice]
            pf, pw = float(ev.p_foul[ev.choice]), float(ev.p_water[ev.choice])
        unc = ev.unconstrained
        held = ev.choice is not None and unc is not None and ev.choice > unc
        binding = None
        if ev.choice is not None and ev.choice > 0:
            prev = ev.choice - 1
            names = []
            if ev.p_foul[prev] > lim.fouling_risk_budget:
                names.append("fouling")
            if ev.p_water[prev] > lim.water_risk_budget:
                names.append("water_security")
            if not ev.allowed[prev]:
                names.append("dwell")
            binding = " and ".join(names) or "hysteresis"
        out.append(DayAdvice(day, a, q, pf, pw, float(ev.p_foul[0]), binding, bool(held)))
        if (a, q) == (cur_a, cur_q):
            hours += 24.0
        else:
            cur_a, cur_q, hours = a, q, 24.0
    return out


@lru_cache(maxsize=8)
def replay_advice(site: str, draws: int = 400, seed: int = 7) -> tuple[DayAdvice, ...]:
    bs = _series(site, draws, seed)
    return tuple(advise_series(site, bs, 0, len(bs.dates), seed))


WARMUP_DAYS = 30


@lru_cache(maxsize=32)
def window_advice(
    site: str, start: dt.date, end: dt.date, draws: int = 400, seed: int = 7
) -> tuple[DayAdvice, ...]:
    """Advice for [start, end], computed from a warm up of WARMUP_DAYS before ``start`` so that
    the action in force (dwell and hysteresis) has settled. Causal: uses no later evidence."""
    bs = _series(site, draws, seed)
    i0, i1 = bs.index_of(start), bs.index_of(end) + 1
    w0 = max(0, i0 - WARMUP_DAYS)
    return tuple(advise_series(site, bs, w0, i1, seed)[i0 - w0 :])


def timeline(
    site: str, start: dt.date, end: dt.date, draws: int = 400, seed: int = 7
) -> dict[str, Any]:
    bs = _series(site, draws, seed)
    i0, i1 = bs.index_of(start), bs.index_of(end) + 1
    advice = window_advice(site, start, end, draws, seed)
    q = bs.quantiles
    return {
        "label": REPLAY_LABEL,
        "site": site,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "dates": [d.date.isoformat() for d in advice],
        "action": [d.action.value for d in advice],
        "scale": [d.scale for d in advice],
        "p_fouling": [round(d.p_fouling, 5) for d in advice],
        "p_water": [round(d.p_water, 5) for d in advice],
        "p_breach_full": [round(d.p_breach_full, 5) for d in advice],
        "binding": [d.binding for d in advice],
        "dwell_held": [d.dwell_held for d in advice],
        "inspect": [False for _ in advice],
        "clear": [bool(x) for x in bs.clear_obs[i0:i1]],
        "alert": [bool(x) for x in bs.alert[i0:i1]],
        "within_3": {
            k: [round(float(x), 5) for x in q["within_3"][i0:i1, j]]
            for j, k in enumerate(("lo", "median", "hi"))
        },
        "p_any_bloom": {
            k: [round(float(x), 5) for x in q["any_bloom"][i0:i1, j]]
            for j, k in enumerate(("lo", "median", "hi"))
        },
    }


# ---------------------------------------------------------------- Scenario Lab
def scenario_days(sc: Scenario, dr_mean: Draws) -> tuple[list[EvidenceDay], np.ndarray]:
    """Synthetic evidence for a user scenario. Returns the days and the true state per day
    (0 clear, 1 developing, 2 at the intake)."""
    rng = substream(sc.seed, "lab.scenario")
    truth = np.zeros(sc.days, dtype=int)
    if sc.onset_day is not None:
        a = sc.onset_day
        b = min(sc.days, a + sc.days_to_intake)
        c = min(sc.days, b + sc.duration_days)
        truth[a:b] = 1
        truth[b:c] = 2
    alpha = float(dr_mean.alpha[0])
    b_dev = float(dr_mean.beta_dev[0]) if sc.detector_visible else alpha
    b_at = float(dr_mean.beta_at[0]) if sc.detector_visible else alpha
    lik = np.array([alpha, b_dev, b_at])
    clear = rng.random(sc.days) < sc.detector_availability
    alert = clear & (rng.random(sc.days) < lik[truth])
    days = []
    for k in range(sc.days):
        d = sc.start_date + dt.timedelta(days=k)
        if clear[k]:
            state = DetectorState.ALERT if alert[k] else DetectorState.QUIET
            cov, frac = CoverageState.clear, 0.0
        else:
            state, cov, frac = DetectorState.NODATA, CoverageState.nodata, None
        days.append(
            EvidenceDay(
                date=d,
                site=sc.site,
                radius_km=50,
                coverage=cov,
                alert=bool(alert[k]),
                detector_state=state,
                anomaly_fraction=frac,
                source_file="synthetic-scenario",
                source_row=k + 1,
            )
        )
    return days, truth


def run_scenario(sc: Scenario, draws: int = 200) -> dict[str, Any]:
    """Belief, advice and hypothetical plant response day by day for a synthetic scenario."""
    spec = prior_spec(sc.site)
    dr = draw_parameters(spec, draws, sc.seed)
    days, truth = scenario_days(sc, dr.posterior_mean())
    bs = belief_series(sc.site, days, dr)
    prof = default_profile()
    params = sample_params(prof, 1, mode="nominal")
    plant = SimState.initial(1, params, 0.2, 24.0)
    lim = Limits()
    cur_a, cur_q, hours = ActionKind.GO, 1.0, 1000.0
    rows = []
    last_adv: Advisory | None = None
    for i, d in enumerate(bs.dates):
        storage_h = float(plant.storage[0] / params.demand[0])
        state = PlantState(
            fouling_index=float(min(plant.fouling[0], 5.0)),
            storage_hours=storage_h,
            current_action=cur_a,
            current_scale=cur_q,
            hours_in_action=hours,
        )
        inp = from_estimator(
            sc.site,
            issued_at(d),
            bs.result.posterior[i],
            dr,
            d.timetuple().tm_yday,
            prof,
            state,
            lim,
            seed=sc.seed,
            label="SCENARIO: synthetic evidence, hypothetical plant",
        )
        adv = decide(inp)
        last_adv = adv
        q = adv.scale if adv.action != ActionKind.NO_SAFE_OPTION_ESCALATE else _least_bad(adv)
        load = params.background_load + (sc.intensity if truth[i] == 2 else 0.0)
        before_unserved = float(plant.unserved[0])
        simulate(params, np.full((1, 24), load), np.array([q]), plant, "full")
        planned_cleaning(plant, params)
        rows.append(
            {
                "date": d.isoformat(),
                "truth": ["clear", "developing", "at_intake"][truth[i]],
                "clear": bool(bs.clear_obs[i]),
                "alert": bool(bs.alert[i]),
                "p_any_bloom": [round(float(x), 5) for x in bs.quantiles["any_bloom"][i]],
                "within_3": [round(float(x), 5) for x in bs.quantiles["within_3"][i]],
                "action": adv.action.value,
                "scale": adv.scale,
                "binding": adv.binding_constraint,
                "fouling_index": round(float(plant.fouling[0]), 4),
                "storage_hours": round(float(plant.storage[0] / params.demand[0]), 2),
                "unserved_m3": round(float(plant.unserved[0]) - before_unserved, 1),
                "forced_shutdowns": int(plant.forced_shutdowns[0]),
            }
        )
        if (adv.action, adv.scale) == (cur_a, cur_q):
            hours += 24.0
        else:
            cur_a, cur_q, hours = adv.action, adv.scale, 24.0
    assert last_adv is not None
    return {
        "label": "SCENARIO: synthetic evidence, hypothetical plant",
        "scenario": sc.model_dump(mode="json"),
        "days": rows,
        "last_advisory": last_adv.model_dump(mode="json"),
        "totals": {
            "unserved_m3": round(float(plant.unserved[0]), 1),
            "forced_shutdowns": int(plant.forced_shutdowns[0]),
            "cleanings": int(plant.cleanings[0]),
        },
    }


def _least_bad(adv: Advisory) -> float:
    lim = adv.explanation.limits
    best = min(
        adv.explanation.candidates,
        key=lambda c: max(
            c.p_fouling_breach / lim.fouling_risk_budget, c.p_water_breach / lim.water_risk_budget
        ),
    )
    return best.scale
