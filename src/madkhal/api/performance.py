"""Performance budget measurement (build plan section 9).

Wall clock timings on the machine that runs them. Unlike results/e*.json they differ between
runs and machines, so the file records the platform and the number of repetitions, and the
budget check uses the slowest of the repeated measurements where that is the stricter choice.
"""

from __future__ import annotations

import datetime as dt
import os
import platform
import statistics
import time
from pathlib import Path
from typing import Any

from madkhal.contract import REPLAY_LABEL, Limits, PlantState
from madkhal.core.jsonio import read_json
from madkhal.decision import decide, from_estimator
from madkhal.lab.advise import issued_at
from madkhal.lab.replay import belief_replay
from madkhal.plant import default_profile

BUDGET_S = {
    "belief_six_years_400_draws": 5.0,
    "advisory_one": 0.3,
    "experiment_suite": 900.0,
    "api_p95_cached": 0.2,
    "web_first_load_static": 3.0,
}

# Cached GET endpoints: the second and later calls are served from memory.
API_PATHS = (
    "/v1/health",
    "/v1/sites",
    "/v1/evidence/kalba",
    "/v1/track-record",
    "/v1/belief/kalba",
    "/v1/belief/kalba/series",
    "/v1/advisory/kalba",
    "/v1/timeline/kalba",
    "/v1/plant/profile",
    "/v1/plant/sensitivity",
    "/v1/policies/results",
    "/v1/replay/kalba",
    "/v1/method",
    "/v1/claims",
    "/v1/provenance",
    "/v1/missions/kalba",
)


def _timed(fn: Any) -> tuple[float, Any]:
    t0 = time.perf_counter()
    out = fn()
    return time.perf_counter() - t0, out


def measure_belief(site: str = "kalba", repeats: int = 3) -> dict[str, Any]:
    """Belief for one site over the whole OLCI record (2018 to 2023) with 400 draws."""
    times = []
    bs = None
    for _ in range(repeats):
        t, bs = _timed(lambda: belief_replay(site, 400, 7))
        times.append(t)
    assert bs is not None
    return {"site": site, "days": len(bs.dates), "draws": 400, "seconds": times, "max": max(times)}


def measure_advisory(site: str = "kalba", repeats: int = 20) -> dict[str, Any]:
    """One advisory (risk table over every draw and candidate, then the decision) from a belief."""
    bs = belief_replay(site, 400, 7)
    day = bs.dates[-1]
    i = bs.index_of(day)

    def one() -> object:
        inp = from_estimator(
            site,
            issued_at(day),
            bs.result.posterior[i],
            bs.draws,
            day.timetuple().tm_yday,
            default_profile(),
            PlantState(),
            Limits(),
            seed=7,
            label=REPLAY_LABEL,
        )
        return decide(inp)

    one()  # warm up imports and numpy
    times = [_timed(one)[0] for _ in range(repeats)]
    return {
        "site": site,
        "date": day.isoformat(),
        "repeats": repeats,
        "median": statistics.median(times),
        "max": max(times),
    }


def measure_api(repeats: int = 30) -> dict[str, Any]:
    """p95 latency per cached endpoint through the ASGI stack (in process, no network)."""
    from fastapi.testclient import TestClient

    from .app import create_app

    client = TestClient(create_app())
    per_path: dict[str, Any] = {}
    for p in API_PATHS:
        first, r = _timed(lambda p=p: client.get(p))
        if r.status_code != 200:
            raise RuntimeError(f"{p} answered {r.status_code}")
        times = sorted(_timed(lambda p=p: client.get(p))[0] for _ in range(repeats))
        p95 = times[max(0, int(round(0.95 * len(times))) - 1)]
        per_path[p] = {"first_call": round(first, 4), "p95": round(p95, 4)}
    worst = max(v["p95"] for v in per_path.values())
    return {"repeats": repeats, "per_path": per_path, "max_p95": worst}


def _web_first_load(root: Path) -> dict[str, Any] | None:
    path = root / "results" / "performance_web.json"
    return read_json(path) if path.is_file() else None


def measure_all(root: Path) -> dict[str, Any]:
    belief = measure_belief()
    advisory = measure_advisory()
    api = measure_api()
    run = read_json(root / "results" / "run.json")
    web = _web_first_load(root)
    observed = {
        "belief_six_years_400_draws": belief["max"],
        "advisory_one": advisory["max"],
        "experiment_suite": float(run["seconds_total"]),
        "api_p95_cached": api["max_p95"],
        "web_first_load_static": None if web is None else float(web["max"]),
    }
    budget = {
        k: {
            "budget_s": BUDGET_S[k],
            "observed_s": None if v is None else round(v, 4),
            "within": None if v is None else v < BUDGET_S[k],
        }
        for k, v in observed.items()
    }
    return {
        "note": (
            "Wall clock timings on one machine; they vary between runs. The experiment suite "
            "time is the recorded seconds_total of the run that wrote results/e*.json "
            "(results/run.json). The web first load comes from results/performance_web.json, "
            "written by the Playwright performance test."
        ),
        "measured_on": dt.date.today().isoformat(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "budget": budget,
        "detail": {"belief": belief, "advisory": advisory, "api": api, "web": web},
    }
