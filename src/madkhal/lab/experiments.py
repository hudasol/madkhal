"""Preregistered experiments E1 to E7 (docs/PREREGISTRATION.md). Returns plain dicts; the CLI
writes them to results/*.json. Synthetic worlds except E7, which replays real evidence.
"""

from __future__ import annotations

import datetime as dt
import math
import os
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from typing import Any

import numpy as np

from madkhal.contract import REPLAY_LABEL, ActionKind
from madkhal.decision import CostWeights, SurveyConfig
from madkhal.estimator import (
    alert_means_bloom,
    brier,
    draw_parameters,
    interval_coverage,
    log_score,
    persistence,
    reliability,
    run_filter,
)
from madkhal.plant import default_profile

from .advise import _series, replay_advice
from .generators import DETECTOR_KEYS, SITE, g1, truth_detector, world
from .inputs import prior_spec, snapshot
from .policies import POLICIES, POLICY_NAMES
from .replay import REPLAY_SITES, event_points
from .simulation import LAB_DRAWS, LAB_SEED, run_policy, summarise

EVAL_SEEDS = tuple(range(1000, 1030))
E4_SEEDS = tuple(range(1000, 1020))
E5_SEEDS = tuple(range(1000, 1010))
E5_RANDOM = 40
E4_AVAILABILITY = (0.2, 0.6, 1.0)
E4_COSTS = (250.0, 1000.0, 4000.0, 16000.0)
COST_PARTS = (
    "forced_shutdowns",
    "cleanings",
    "unserved_m3",
    "membrane_index",
    "derate_days",
    "restarts",
    "sorties",
)
METRIC_UNITS = {
    "unserved_m3": "m3",
    "forced_shutdowns": "count per 2 years",
    "cleanings": "count per 2 years",
    "membrane_index": "index",
    "park_days_per_year": "days per year",
    "derate_days_per_year": "days per year",
    "escalation_days_per_year": "days per year",
    "changes_per_30_days": "changes per 30 days",
    "sorties_per_year": "sorties per year",
    "restarts": "count per 2 years",
    "weighted_cost_cu": "CU per 2 years",
    "dwell_compliance": "share",
}


def chunks(seq: Sequence[int], k: int) -> list[list[int]]:
    k = max(1, min(k, len(seq)))
    return [list(seq[i::k]) for i in range(k)]


# ---------------------------------------------------------------- workers (top level for spawn)
def _policy_task(args: tuple[str, str, list[int], dict[str, Any]]) -> dict[str, Any]:
    generator, policy, seeds, opts = args
    worlds = []
    for s in seeds:
        if generator == "G1" and (opts.get("plant_mult") or opts.get("detector_mult")):
            worlds.append(
                g1(s, plant_mult=opts.get("plant_mult"), detector_mult=opts.get("detector_mult"))
            )
        else:
            worlds.append(world(generator, s))
    survey = SurveyConfig(
        availability=opts.get("availability", 0.8), cost_cu=opts.get("cost", 1000.0)
    )
    r = run_policy(policy, worlds, survey=survey)
    years = worlds[0].days / 365.0
    parts = {
        "forced_shutdowns": r.metrics["forced_shutdowns"],
        "cleanings": r.metrics["cleanings"],
        "unserved_m3": r.metrics["unserved_m3"],
        "membrane_index": r.metrics["membrane_index"],
        "derate_days": r.metrics["derate_days_per_year"] * years,
        "restarts": r.metrics["restarts"],
        "sorties": r.metrics["sorties_per_year"] * years,
    }
    return {
        "seeds": seeds,
        "metrics": {k: v.tolist() for k, v in r.metrics.items()},
        "parts": {k: np.asarray(v).tolist() for k, v in parts.items()},
        "sortie_cost": survey.cost_cu,
    }


def _e1_task(seeds: list[int]) -> dict[str, Any]:
    dr = draw_parameters(prior_spec(SITE), LAB_DRAWS, LAB_SEED)
    truth = truth_detector(SITE)
    out: dict[str, Any] = {
        "per_seed": [],
        "forecast": [],
        "outcome": [],
        "lo": [],
        "hi": [],
        "p_true": [],
    }
    for s in seeds:
        w = world("G1", s)
        res = run_filter(w.clear, w.alert, w.doy, dr, horizons=(3,))
        p = np.median(res.within[0], axis=1)
        lo = np.quantile(res.within[0], 0.05, axis=1)
        hi = np.quantile(res.within[0], 0.95, axis=1)
        p_true = run_filter(w.clear, w.alert, w.doy, truth, horizons=(3,)).within[0][:, 0]
        y = w.at_within(3).astype(float)
        base_a = alert_means_bloom(w.alert)
        base_p = persistence(w.alert, 7)
        out["per_seed"].append(
            {
                "seed": s,
                "brier": {
                    "madkhal": brier(p, y),
                    "alert_means_bloom": brier(base_a, y),
                    "persistence": brier(base_p, y),
                },
                "log_score": {
                    "madkhal": log_score(p, y),
                    "alert_means_bloom": log_score(base_a, y),
                    "persistence": log_score(base_p, y),
                },
                "coverage90": interval_coverage(lo, hi, p_true),
                "bloom_days": int(y.sum()),
            }
        )
        out["forecast"] += p.tolist()
        out["outcome"] += y.tolist()
    return out


def _parallel(fn: Callable[[Any], Any], tasks: list[Any], workers: int) -> list[Any]:
    if workers <= 1:
        return [fn(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, tasks))


def _merge(parts: list[dict[str, Any]]) -> dict[str, Any]:
    seeds: list[int] = []
    metrics: dict[str, list[float]] = {}
    pp: dict[str, list[float]] = {}
    for p in parts:
        seeds += p["seeds"]
        for k, v in p["metrics"].items():
            metrics.setdefault(k, []).extend(v)
        for k, v in p["parts"].items():
            pp.setdefault(k, []).extend(v)
    order = np.argsort(seeds)
    return {
        "seeds": [seeds[i] for i in order],
        "metrics": {k: [v[i] for i in order] for k, v in metrics.items()},
        "parts": {k: [v[i] for i in order] for k, v in pp.items()},
        "sortie_cost": parts[0]["sortie_cost"],
    }


def weighted(parts: dict[str, list[float]], w: CostWeights, sortie_cost: float) -> np.ndarray:
    a = {k: np.asarray(v, float) for k, v in parts.items()}
    out: np.ndarray = (
        a["forced_shutdowns"] * w.forced_shutdown
        + a["cleanings"] * w.cleaning
        + a["unserved_m3"] * w.unserved_m3
        + a["membrane_index"] * w.membrane_index
        + a["derate_days"] * w.derate_day
        + a["restarts"] * w.restart
        + a["sorties"] * sortie_cost
    )
    return out


# ---------------------------------------------------------------- E1
def e1(seeds: Sequence[int] = EVAL_SEEDS, workers: int = 1) -> dict[str, Any]:
    parts = _parallel(_e1_task, chunks(seeds, workers), workers)
    per = sorted([r for p in parts for r in p["per_seed"]], key=lambda r: r["seed"])
    f = np.concatenate([np.asarray(p["forecast"]) for p in parts])
    y = np.concatenate([np.asarray(p["outcome"]) for p in parts])
    out: dict[str, Any] = {
        "experiment": "E1",
        "generator": "G1",
        "seeds": [r["seed"] for r in per],
        "label": "SYNTHETIC",
    }
    for score in ("brier", "log_score"):
        out[score] = {
            m: summarise(np.array([r[score][m] for r in per]))
            for m in ("madkhal", "alert_means_bloom", "persistence")
        }
    out["coverage90"] = summarise(np.array([r["coverage90"] for r in per]), "share")
    rel = reliability(f, y, bins=10)
    out["reliability"] = rel
    big = [b for b in rel if b["n"] >= 50]
    out["reliability_bins_ok"] = {
        "bins_with_50_days": len(big),
        "bins_within_0_1": sum(1 for b in big if abs(b["observed"] - b["mean_forecast"]) <= 0.1),
    }
    out["per_seed"] = per
    return out


# ---------------------------------------------------------------- E2, E3
def policy_runs(
    generator: str,
    seeds: Sequence[int],
    workers: int,
    opts: dict[str, Any] | None = None,
    policies: Sequence[str] = POLICIES,
) -> dict[str, dict[str, Any]]:
    o = opts or {}
    tasks = [
        (generator, p, ch, o)
        for p in policies
        for ch in chunks(seeds, max(1, workers // len(policies)) or 1)
    ]
    res = _parallel(_policy_task, tasks, workers)
    out: dict[str, dict[str, Any]] = {}
    for p in policies:
        out[p] = _merge([r for t, r in zip(tasks, res, strict=True) if t[1] == p])
    return out


def compare(runs: dict[str, dict[str, Any]], generator: str) -> dict[str, Any]:
    w = CostWeights()
    oracle_cost = weighted(runs["P5"]["parts"], w, runs["P5"]["sortie_cost"])
    out: dict[str, Any] = {"generator": generator, "seeds": runs["P0"]["seeds"], "policies": {}}
    for p, r in runs.items():
        cost = weighted(r["parts"], w, r["sortie_cost"])
        out["policies"][p] = {
            "name": POLICY_NAMES[p],
            "metrics": {
                k: summarise(np.asarray(v), METRIC_UNITS.get(k, ""))
                for k, v in r["metrics"].items()
            },
            "regret_cu": summarise(cost - oracle_cost, "CU per 2 years"),
            "regret_per_seed": (cost - oracle_cost).tolist(),
        }
    # weight sensitivity: halve and double each weight, regret ranking of the non oracle policies
    sens = {}
    for name in (
        "forced_shutdown",
        "cleaning",
        "unserved_m3",
        "membrane_index",
        "derate_day",
        "restart",
    ):
        for factor in (0.5, 2.0):
            ww = w.scaled(name, factor)
            oc = weighted(runs["P5"]["parts"], ww, runs["P5"]["sortie_cost"])
            reg = {
                p: float(np.mean(weighted(r["parts"], ww, r["sortie_cost"]) - oc))
                for p, r in runs.items()
                if p != "P5"
            }
            sens[f"{name} x{factor:g}"] = {
                "mean_regret_cu": reg,
                "ranking": sorted(reg, key=lambda k: reg[k]),
            }
    out["weights"] = w.__dict__
    out["weight_sensitivity"] = sens
    out["weight_sensitivity_note"] = "The oracle is not re optimised for the changed weights."
    return out


# ---------------------------------------------------------------- E4
def e4(workers: int, base_p3: dict[str, Any] | None = None) -> dict[str, Any]:
    seeds = E4_SEEDS
    p3 = base_p3 or policy_runs("G1", seeds, workers, policies=("P3",))["P3"]
    w = CostWeights()
    idx = [p3["seeds"].index(s) for s in seeds]
    p3_parts = {k: [v[i] for i in idx] for k, v in p3["parts"].items()}
    p3_cost = weighted(p3_parts, w, 0.0)
    tasks = [
        ("G1", "P4", ch, {"availability": a, "cost": c})
        for a in E4_AVAILABILITY
        for c in E4_COSTS
        for ch in chunks(seeds, 2)
    ]
    res = _parallel(_policy_task, tasks, workers)
    grid: list[dict[str, Any]] = []
    for a in E4_AVAILABILITY:
        for c in E4_COSTS:
            parts = _merge(
                [
                    r
                    for t, r in zip(tasks, res, strict=True)
                    if t[3] == {"availability": a, "cost": c}
                ]
            )
            cost = weighted(parts["parts"], w, c)
            grid.append(
                {
                    "availability": a,
                    "sortie_cost_cu": c,
                    "p4_minus_p3_cu": summarise(cost - p3_cost, "CU per 2 years"),
                    "p4_cost_cu": summarise(cost, "CU per 2 years"),
                    "sorties_per_year": summarise(
                        np.asarray(parts["metrics"]["sorties_per_year"]), "sorties per year"
                    ),
                }
            )
    # break even at availability 1.0: interpolate the cost where P4 minus P3 crosses zero
    row = [g for g in grid if g["availability"] == 1.0]
    diffs: list[tuple[float, float]] = [
        (float(g["sortie_cost_cu"]), float(g["p4_minus_p3_cu"]["mean"])) for g in row
    ]
    be: dict[str, Any] = {"availability": 1.0}
    if all(d >= 0 for _, d in diffs):
        be.update(
            {
                "break_even_cost_cu": None,
                "note": f"INSPECT does not pay at any tested cost (lowest {diffs[0][0]:g} CU)",
            }
        )
    elif all(d < 0 for _, d in diffs):
        be.update(
            {
                "break_even_cost_cu": None,
                "note": f"INSPECT pays at every tested cost (highest {diffs[-1][0]:g} CU)",
            }
        )
    else:
        val = None
        for (c0, d0), (c1, d1) in zip(diffs, diffs[1:], strict=False):
            if d0 < 0 <= d1:
                f = d0 / (d0 - d1)
                val = math.exp(math.log(c0) + f * (math.log(c1) - math.log(c0)))
                break
        be.update(
            {"break_even_cost_cu": val, "note": "log linear interpolation between grid costs"}
        )
    return {
        "experiment": "E4",
        "generator": "G1",
        "seeds": list(seeds),
        "label": "SYNTHETIC",
        "grid": grid,
        "break_even": be,
        "p3_cost_cu": summarise(p3_cost, "CU per 2 years"),
    }


# ---------------------------------------------------------------- E5
def e5(workers: int) -> dict[str, Any]:
    prof = default_profile()
    physics = [
        p
        for p in prof.parameters
        if p.role == "physics" and p.key not in ("plant.planned_clean_at",)
    ]
    w = CostWeights()
    variants: list[tuple[str, str, float, dict[str, Any]]] = []
    for p in physics:
        for sign in (1.0, -1.0):
            variants.append(
                (p.key, "plant", sign, {"plant_mult": {p.key: math.exp(sign * p.rel_spread)}})
            )
    for key in DETECTOR_KEYS:
        for sign in (1.0, -1.0):
            variants.append(
                (
                    f"detector.{key}",
                    "detector",
                    sign,
                    {"detector_mult": {key: math.exp(sign * 0.3)}},
                )
            )
    tasks = [("G1", pol, list(E5_SEEDS), v[3]) for v in variants for pol in ("P3", "P5")]
    res = _parallel(_policy_task, tasks, workers)
    regrets: dict[tuple[str, float], float] = {}
    for vi, v in enumerate(variants):
        r3, r5 = res[2 * vi], res[2 * vi + 1]
        regrets[(v[0], v[2])] = float(
            np.mean(weighted(r3["parts"], w, 0.0) - weighted(r5["parts"], w, 0.0))
        )
    oat: list[dict[str, Any]] = []
    for key in dict.fromkeys(v[0] for v in variants):
        hi, lo = regrets[(key, 1.0)], regrets[(key, -1.0)]
        oat.append(
            {"key": key, "regret_plus_cu": hi, "regret_minus_cu": lo, "swing_cu": abs(hi - lo)}
        )
    oat.sort(key=lambda r: -r["swing_cu"])
    # random design: each sample moves every parameter by a normal multiple of its spread
    rng = np.random.default_rng(20261013)
    samples = []
    rtasks = []
    keys = [p.key for p in physics] + [f"detector.{k}" for k in DETECTOR_KEYS]
    spreads = [p.rel_spread for p in physics] + [0.3] * len(DETECTOR_KEYS)
    for i in range(E5_RANDOM):
        z = rng.standard_normal(len(keys))
        mult = {k: math.exp(s * zz) for k, s, zz in zip(keys, spreads, z, strict=True)}
        samples.append(z.tolist())
        opts = {
            "plant_mult": {k: m for k, m in mult.items() if k.startswith("plant.")},
            "detector_mult": {
                k.removeprefix("detector."): m for k, m in mult.items() if k.startswith("detector.")
            },
        }
        seed = EVAL_SEEDS[i % len(EVAL_SEEDS)]
        rtasks += [("G1", "P3", [seed], opts), ("G1", "P5", [seed], opts)]
    rres = _parallel(_policy_task, rtasks, workers)
    reg = np.array(
        [
            float(
                weighted(rres[2 * i]["parts"], w, 0.0)[0]
                - weighted(rres[2 * i + 1]["parts"], w, 0.0)[0]
            )
            for i in range(E5_RANDOM)
        ]
    )
    zs = np.array(samples)
    rank_corr: list[dict[str, Any]] = []
    for j, k in enumerate(keys):
        rank_corr.append({"key": k, "spearman": _spearman(zs[:, j], reg)})
    rank_corr.sort(key=lambda r: -abs(r["spearman"]))
    return {
        "experiment": "E5",
        "generator": "G1",
        "label": "SYNTHETIC",
        "oat_seeds": list(E5_SEEDS),
        "one_at_a_time": oat,
        "random_design_samples": E5_RANDOM,
        "rank_correlation": rank_corr,
        "measure_first": [r["key"] for r in rank_corr[:3]],
    }


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


# ---------------------------------------------------------------- E6
def e6(g1_runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "experiment": "E6",
        "generator": "G1",
        "label": "SYNTHETIC",
        "policies": {},
    }
    for p in ("P3", "P4"):
        m = g1_runs[p]["metrics"]
        out["policies"][p] = {
            "changes_per_30_days": summarise(
                np.asarray(m["changes_per_30_days"]), "changes per 30 days"
            ),
            "dwell_compliance": summarise(np.asarray(m["dwell_compliance"]), "share"),
        }
    out["note"] = (
        "Daily decisions: the 12 hour dwell cannot bind; the hysteresis margin does the work (ADR 0008)."
    )
    return out


# ---------------------------------------------------------------- E7
def e7(draws: int = 400, seed: int = 7) -> dict[str, Any]:
    snap = snapshot()
    sites = {}
    for site in REPLAY_SITES:
        adv = replay_advice(site, draws, seed)
        bs = _series(site, draws, seed)
        quiet = snap.quiet_dates(site)
        windows = snap.event_window_dates(site)
        excluded_years = snap.excluded_years(site)
        by_year: dict[str, dict[str, int]] = {}
        for a in adv:
            y = str(a.date.year)
            row = by_year.setdefault(
                y,
                {
                    "days": 0,
                    "non_go": 0,
                    "quiet_days": 0,
                    "quiet_non_go": 0,
                    "outside_windows": 0,
                    "outside_non_go": 0,
                },
            )
            non_go = a.action != ActionKind.GO
            row["days"] += 1
            row["non_go"] += non_go
            if a.date in quiet:
                row["quiet_days"] += 1
                row["quiet_non_go"] += non_go
            if a.date not in windows and a.date.year not in excluded_years:
                row["outside_windows"] += 1
                row["outside_non_go"] += non_go
        q_days = sum(r["quiet_days"] for r in by_year.values())
        q_non = sum(r["quiet_non_go"] for r in by_year.values())
        o_days = sum(r["outside_windows"] for r in by_year.values())
        o_non = sum(r["outside_non_go"] for r in by_year.values())
        points = []
        index = {a.date: a for a in adv}
        for pt in event_points(site):
            row2: dict[str, Any] = {
                "event_id": pt.event_id,
                "label": pt.label,
                "status_badge": pt.status_badge,
                "anchor": pt.anchor,
                "anchor_date": pt.anchor_date.isoformat(),
                "days_before": pt.days_before,
                "date": pt.date.isoformat(),
            }
            if pt.in_range:
                a = index[pt.date]
                i = bs.index_of(pt.date)
                row2.update(
                    {
                        "action": a.action.value,
                        "scale": a.scale,
                        "p_any_bloom": [float(x) for x in bs.quantiles["any_bloom"][i]],
                        "within_3": [float(x) for x in bs.quantiles["within_3"][i]],
                    }
                )
            else:
                row2["note"] = "before the start of the satellite record"
            points.append(row2)
        sites[site] = {
            "by_year": by_year,
            "quiet_non_go_per_year": 365.0 * q_non / q_days if q_days else None,
            "quiet_days": q_days,
            "quiet_non_go_days": q_non,
            "outside_windows_non_go_per_year": 365.0 * o_non / o_days if o_days else None,
            "outside_windows_days": o_days,
            "outside_windows_non_go_days": o_non,
            "points": points,
        }
    return {"experiment": "E7", "label": REPLAY_LABEL, "draws": draws, "seed": seed, "sites": sites}


# ---------------------------------------------------------------- all
def run_all(
    seeds: Sequence[int] = EVAL_SEEDS,
    workers: int | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, dict[str, Any]]:
    w = workers or max(1, min(15, (os.cpu_count() or 2) - 1))
    t0 = time.perf_counter()
    timings: dict[str, float] = {}
    out: dict[str, dict[str, Any]] = {}

    def stamp(name: str, t: float) -> None:
        timings[name] = round(time.perf_counter() - t, 1)
        log(f"{name} done in {timings[name]} s")

    t = time.perf_counter()
    out["e1"] = e1(seeds, w)
    stamp("E1", t)
    t = time.perf_counter()
    g1_runs = policy_runs("G1", seeds, w)
    e2 = compare(g1_runs, "G1")
    e2.update({"experiment": "E2", "label": "SYNTHETIC"})
    out["e2"] = e2
    stamp("E2", t)
    t = time.perf_counter()
    g2_runs = policy_runs("G2", seeds, w)
    e3 = compare(g2_runs, "G2")
    e3.update({"experiment": "E3", "label": "SYNTHETIC"})
    e3["drop"] = {
        p: {
            "regret_g1_cu": e2["policies"][p]["regret_cu"]["mean"],
            "regret_g2_cu": e3["policies"][p]["regret_cu"]["mean"],
            "regret_change_cu": e3["policies"][p]["regret_cu"]["mean"]
            - e2["policies"][p]["regret_cu"]["mean"],
        }
        for p in POLICIES
    }
    out["e3"] = e3
    stamp("E3", t)
    t = time.perf_counter()
    if set(E4_SEEDS) <= set(seeds):
        out["e4"] = e4(w, g1_runs["P3"])
        stamp("E4", t)
    t = time.perf_counter()
    if set(E5_SEEDS) <= set(seeds):
        out["e5"] = e5(w)
        stamp("E5", t)
    out["e6"] = e6(g1_runs)
    t = time.perf_counter()
    out["e7"] = e7()
    stamp("E7", t)
    out["run"] = {
        "seeds": list(seeds),
        "workers": w,
        "seconds_total": round(time.perf_counter() - t0, 1),
        "seconds_by_experiment": timings,
        "lab_draws": LAB_DRAWS,
        "created_for": "docs/PREREGISTRATION.md",
        "date": dt.date.today().isoformat(),
    }
    return out
