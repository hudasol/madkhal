"""Run one policy over many synthetic worlds, day by day, with the plant vectorised over worlds.

SYNTHETIC: generator worlds and a hypothetical plant. Results are written by the experiments
module; nothing here reads or writes files.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from madkhal.contract import ActionKind, Limits, PlantState, restrictiveness
from madkhal.decision import CostWeights, SurveyConfig
from madkhal.estimator import burn_in, draw_parameters, propagate, survey_update, update
from madkhal.plant import PlantParams, default_profile, planned_cleaning
from madkhal.plant import PlantState as SimState
from madkhal.plant import simulate as plant_simulate

from . import policies as pol
from .advise import TableCache
from .generators import SITE, World
from .inputs import prior_spec

LAB_DRAWS = 100
LAB_SEED = 7
FOULING_STEP = 0.05
STORAGE_STEP_H = 2.0


@dataclass
class RunResult:
    policy: str
    generator: str
    seeds: list[int]
    metrics: dict[str, np.ndarray]  # name -> (lanes,)
    actions: list[list[str]] = field(default_factory=list)  # per lane, per day "GO:1.0"


def stack_params(worlds: list[World]) -> PlantParams:
    fields = PlantParams.__dataclass_fields__
    return PlantParams(**{f: np.concatenate([getattr(w.plant, f) for w in worlds]) for f in fields})


def observed_state(
    fouling: float, storage_h: float, action: ActionKind, scale: float, hours: float
) -> PlantState:
    """What the operator sees, rounded conservatively: fouling up, storage down."""
    f = min(math.ceil(max(fouling, 0.0) / FOULING_STEP - 1e-9) * FOULING_STEP, 1.5)
    s = max(math.floor(storage_h / STORAGE_STEP_H + 1e-9) * STORAGE_STEP_H, 0.0)
    return PlantState(
        fouling_index=round(f, 6),
        storage_hours=round(min(s, 72.0), 6),
        current_action=action,
        current_scale=scale,
        hours_in_action=hours,
    )


def run_policy(
    policy: str,
    worlds: list[World],
    weights: CostWeights | None = None,
    survey: SurveyConfig | None = None,
    limits: Limits | None = None,
    draws: int = LAB_DRAWS,
    cache: TableCache | None = None,
    record_actions: bool = False,
) -> RunResult:
    if policy not in pol.POLICIES:
        raise ValueError(f"unknown policy {policy}")
    w = weights or CostWeights()
    sv = survey or SurveyConfig()
    lim = limits or Limits()
    n = len(worlds)
    days = worlds[0].days
    params = stack_params(worlds)
    st = SimState.initial(n, params, 0.2, 24.0)
    profile = default_profile()
    dr = draw_parameters(prior_spec(SITE), draws, LAB_SEED)
    ctx = pol.MadkhalContext(SITE, dr, profile, lim, LAB_SEED)
    tc = cache or TableCache()
    beliefs = [burn_in(int(wd.doy[0]), dr) for wd in worlds] if policy in ("P3", "P4") else []
    cur_a = [ActionKind.GO] * n
    cur_q = [1.0] * n
    hours = [1000.0] * n
    changes = np.zeros(n)
    relax_changes = np.zeros(n)
    relax_ok = np.zeros(n)
    park_days = np.zeros(n)
    derate_days = np.zeros(n)
    escalations = np.zeros(n)
    sorties = np.zeros(n)
    acts: list[list[str]] = [[] for _ in range(n)]
    sensor = sv.sensor
    for t in range(days):
        q = np.ones(n)
        outs: list[pol.PolicyOutput] = []
        if policy == "P5":
            future = np.zeros((n, 24 * pol.ORACLE_HORIZON_DAYS))
            for i, wd in enumerate(worlds):
                for k in range(pol.ORACLE_HORIZON_DAYS):
                    tt = min(t + k, days - 1)
                    future[i, 24 * k : 24 * (k + 1)] = params.background_load[i] + wd.bloom_load[tt]
            q = pol.oracle(params, st, future, w)
            for i in range(n):
                qi = float(q[i])
                a = (
                    ActionKind.GO
                    if qi >= 1.0
                    else (ActionKind.PARK if qi <= 0.0 else ActionKind.DERATE)
                )
                outs.append(pol.PolicyOutput(a, qi))
        else:
            for i, wd in enumerate(worlds):
                day = wd.dates[t]
                if policy == "P0":
                    out = pol.always_go()
                elif policy == "P1":
                    out = pol.alert_park(wd.alert[: t + 1])
                elif policy == "P2":
                    out = pol.seasonal_rule(day)
                else:
                    b = propagate(beliefs[i], int(wd.doy[t]), dr)
                    b = update(b, bool(wd.clear[t]), bool(wd.alert[t]), dr)
                    storage_h = float(st.storage[i] / params.demand[i])
                    obs = observed_state(
                        float(st.fouling[i]), storage_h, cur_a[i], cur_q[i], hours[i]
                    )
                    if policy == "P4":
                        ins = pol.inspect_request(ctx, day, int(wd.doy[t]), b, obs, tc, sv, w)
                        if ins.inspect and wd.survey_fly_u[t] < sv.availability:
                            sorties[i] += 1
                            truth = int(wd.truth_state3()[t])
                            p_det = (sensor.p_clear, sensor.p_developing, sensor.p_at_intake)[truth]
                            b = survey_update(b, bool(wd.survey_det_u[t] < p_det), sensor)
                    beliefs[i] = b
                    out = pol.madkhal(ctx, day, int(wd.doy[t]), b, obs, tc)
                outs.append(out)
                q[i] = out.scale
        for i, out in enumerate(outs):
            if (out.action, out.scale) != (cur_a[i], cur_q[i]):
                changes[i] += 1
                if restrictiveness(out.action, out.scale) < restrictiveness(cur_a[i], cur_q[i]):
                    relax_changes[i] += 1
                    relax_ok[i] += hours[i] >= lim.dwell_hours
                cur_a[i], cur_q[i], hours[i] = out.action, out.scale, 24.0
            else:
                hours[i] += 24.0
            park_days[i] += out.action == ActionKind.PARK
            derate_days[i] += out.action == ActionKind.DERATE
            escalations[i] += out.escalated
            if record_actions:
                acts[i].append(f"{out.action.value}:{out.scale:.1f}")
        load = np.stack(
            [params.background_load + np.array([wd.bloom_load[t] for wd in worlds])] * 24, axis=1
        )
        plant_simulate(params, load, q, st, "full")
        planned_cleaning(st, params)
    years = days / 365.0
    cost = (
        st.forced_shutdowns * w.forced_shutdown
        + st.cleanings * w.cleaning
        + st.unserved * w.unserved_m3
        + st.wear * w.membrane_index
        + derate_days * w.derate_day
        + st.restarts * w.restart
        + sorties * sv.cost_cu
    )
    metrics = {
        "unserved_m3": st.unserved.copy(),
        "forced_shutdowns": st.forced_shutdowns.copy(),
        "cleanings": st.cleanings.copy(),
        "membrane_index": st.wear.copy(),
        "park_days_per_year": park_days / years,
        "derate_days_per_year": derate_days / years,
        "escalation_days_per_year": escalations / years,
        "changes_per_30_days": changes / (days / 30.0),
        "sorties_per_year": sorties / years,
        "restarts": st.restarts.copy(),
        "weighted_cost_cu": cost,
        "dwell_compliance": np.where(
            relax_changes > 0, relax_ok / np.maximum(relax_changes, 1), 1.0
        ),
    }
    return RunResult(policy, worlds[0].generator, [wd.seed for wd in worlds], metrics, acts)


def summarise(values: np.ndarray, unit: str = "") -> dict[str, Any]:
    """Mean with a 95 percent interval (mean plus or minus 1.96 standard errors)."""
    v = np.asarray(values, float)
    n = v.size
    mean = float(v.mean())
    se = float(v.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    return {"mean": mean, "lo": mean - 1.96 * se, "hi": mean + 1.96 * se, "n": n, "unit": unit}
