"""Cached computations behind the API. Pure apart from reading the verified snapshot once."""

from __future__ import annotations

import datetime as dt
from functools import lru_cache
from typing import Any

from madkhal import __version__
from madkhal.contract import (
    ADVISORY_SCOPE,
    BANNER_EVIDENCE,
    BANNER_HYPOTHETICAL,
    Advisory,
    BloomBelief,
    Dataset,
    PlantState,
    Scenario,
    Site,
    TrackRecord,
)
from madkhal.core import paths
from madkhal.core.errors import InputError, MadkhalError, UnknownSiteError
from madkhal.core.jsonio import read_json
from madkhal.estimator import BeliefSeries
from madkhal.evidence import PINNED_COMMIT, RADII, monthly_clear_share, yearly_counts
from madkhal.lab import advise
from madkhal.lab.inputs import snapshot
from madkhal.lab.replay import belief_replay
from madkhal.plant import default_profile, tornado

DEFAULT_DRAWS = 400
DEFAULT_SEED = 7
MAX_DRAWS = 1000
OLCI_SITES = ("kalba", "barka", "alraha")


def check_site(site: str) -> str:
    if site not in OLCI_SITES:
        raise UnknownSiteError(f"unknown site '{site}'; expected one of {', '.join(OLCI_SITES)}")
    return site


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "evidence_commit": PINNED_COMMIT,
        "banner": {"evidence": BANNER_EVIDENCE, "hypothetical": BANNER_HYPOTHETICAL},
        "scope": ADVISORY_SCOPE,
    }


def sites(dataset: Dataset = Dataset.olci_v1) -> list[Site]:
    return snapshot().sites(dataset)


@lru_cache(maxsize=16)
def series(site: str, draws: int = DEFAULT_DRAWS, seed: int = DEFAULT_SEED) -> BeliefSeries:
    check_site(site)
    return belief_replay(site, draws, seed)


def parse_date(site: str, text: str | None) -> dt.date:
    bs = series(site)
    if text is None:
        return bs.dates[-1]
    try:
        d = dt.date.fromisoformat(text)
    except ValueError:
        raise InputError(f"date must be an ISO date (YYYY-MM-DD), got '{text}'") from None
    if not bs.dates[0] <= d <= bs.dates[-1]:
        raise InputError(f"date must be within {bs.dates[0]} and {bs.dates[-1]} for {site}")
    return d


def belief(site: str, date: str | None, draws: int, seed: int) -> BloomBelief:
    check_site(site)
    bs = series(site, draws, seed)
    return bs.to_belief(bs.index_of(parse_date(site, date)))


def belief_series(site: str, start: str | None, end: str | None) -> dict[str, Any]:
    check_site(site)
    bs = series(site)
    d0 = parse_date(site, start) if start else bs.dates[0]
    d1 = parse_date(site, end) if end else bs.dates[-1]
    if d1 < d0:
        raise InputError("end must not be before start")
    i0, i1 = bs.index_of(d0), bs.index_of(d1) + 1
    q = bs.quantiles

    def cols(name: str) -> dict[str, list[float]]:
        a = q[name][i0:i1]
        return {
            "lo": [round(float(x), 5) for x in a[:, 0]],
            "median": [round(float(x), 5) for x in a[:, 1]],
            "hi": [round(float(x), 5) for x in a[:, 2]],
        }

    return {
        "site": site,
        "start": d0.isoformat(),
        "end": d1.isoformat(),
        "level": 0.9,
        "n_draws": bs.draws.n,
        "seed": bs.draws.seed,
        "dates": [d.isoformat() for d in bs.dates[i0:i1]],
        "clear": [bool(x) for x in bs.clear_obs[i0:i1]],
        "alert": [bool(x) for x in bs.alert[i0:i1]],
        "staleness_days": [int(x) if x >= 0 else None for x in bs.staleness[i0:i1]],
        "p_any_bloom": cols("any_bloom"),
        "p_at_intake": cols("at_intake"),
        "within_1": cols("within_1"),
        "within_3": cols("within_3"),
        "within_7": cols("within_7"),
    }


def evidence(site: str, radius: int) -> dict[str, Any]:
    check_site(site)
    if radius not in RADII:
        raise InputError(f"radius must be one of {list(RADII)}")
    snap = snapshot()
    days = snap.evidence_days(site, radius=radius)
    states = []
    for d in days:
        if d.coverage.value == "nodata":
            states.append("nodata")
        else:
            states.append("alert" if d.alert else "clear")
    share = monthly_clear_share(days)
    events = [e for e in snap.events() if e.site == site and e.dataset == Dataset.olci_v1]
    return {
        "site": site,
        "radius_km": radius,
        "dataset": "olci_v1",
        "first_date": days[0].date.isoformat(),
        "last_date": days[-1].date.isoformat(),
        "dates": [d.date.isoformat() for d in days],
        "state": states,
        "anomaly_fraction": [d.anomaly_fraction for d in days],
        "years": {str(k): v for k, v in yearly_counts(days).items()},
        "monthly_clear": {str(m): r.model_dump() for m, r in share.items()},
        "events": [e.model_dump(mode="json") for e in events],
        "source_file": days[0].source_file,
    }


def track_record() -> dict[str, Any]:
    snap = snapshot()
    tr: TrackRecord = snap.track_record()
    anchor = snap.lead_time_anchor()
    vis, vis_cite = snap.detected_episode_alerts()
    out: dict[str, Any] = tr.model_dump(mode="json")
    out["lead_time"] = {
        "event_id": anchor.event_id,
        "lead_alert_days": anchor.lead_alert_days,
        "lead_alert_min_days": anchor.lead_alert_min_days,
        "n": anchor.n,
        "note": "One detected event (n = 1). The range runs from the earliest consistent date to the report date.",
        "source": f"{anchor.source_file} row {anchor.source_row}",
    }
    out["detected_episode_alerts"] = {**vis.model_dump(), "source": vis_cite}
    out["events"] = [e.model_dump(mode="json") for e in snap.events()]
    return out


# ---------------------------------------------------------------- P5: decision and plant
MAX_TIMELINE_DAYS = 400
DEFAULT_TIMELINE_DAYS = 120
PROFILE_ID = "hypothetical-swro-1"


def check_profile(profile_id: str) -> None:
    if profile_id != PROFILE_ID:
        raise UnknownSiteError(f"unknown plant profile '{profile_id}'; expected {PROFILE_ID}")


def advisory(
    site: str, date: str | None, profile_id: str, fouling_index: float, storage_hours: float
) -> Advisory:
    check_site(site)
    check_profile(profile_id)
    day = parse_date(site, date)
    state = PlantState(fouling_index=fouling_index, storage_hours=storage_hours)
    return advise.advisory_for(site, day, DEFAULT_DRAWS, DEFAULT_SEED, state=state)


def timeline(site: str, start: str | None, end: str | None) -> dict[str, Any]:
    check_site(site)
    bs = series(site)
    d1 = parse_date(site, end) if end else bs.dates[-1]
    d0 = (
        parse_date(site, start)
        if start
        else max(bs.dates[0], d1 - dt.timedelta(days=DEFAULT_TIMELINE_DAYS - 1))
    )
    if d1 < d0:
        raise InputError("end must not be before start")
    if (d1 - d0).days + 1 > MAX_TIMELINE_DAYS:
        raise InputError(f"a timeline window is limited to {MAX_TIMELINE_DAYS} days")
    return advise.timeline(site, d0, d1, DEFAULT_DRAWS, DEFAULT_SEED)


def scenario(sc: Scenario) -> dict[str, Any]:
    check_site(sc.site)
    return advise.run_scenario(sc)


def plant_profile() -> dict[str, Any]:
    p = default_profile()
    out: dict[str, Any] = p.model_dump(mode="json")
    out["assumption_share"] = p.assumption_share
    out["evidence_level"] = p.evidence_level.value
    return out


@lru_cache(maxsize=1)
def plant_sensitivity() -> dict[str, Any]:
    prof = default_profile()
    roles = {p.key: p.role for p in prof.parameters}
    rows = [
        {
            "key": r.key,
            "label": r.label,
            "role": roles[r.key],
            "rel_spread": r.rel_spread,
            "swing_fouling": r.swing_fouling,
            "swing_water": r.swing_water,
            "score": r.score,
            "rank": r.rank,
        }
        for r in tornado(prof)
    ]
    measure_first = [
        r["key"] for r in rows if r["role"] == "physics" and float(str(r["score"])) > 0
    ][:3]
    return {
        "method": "One at a time: each parameter moved by plus and minus one spread, others nominal.",
        "rows": rows,
        "measure_first": measure_first,
    }


# ---------------------------------------------------------------- P7 and P8: results, method, missions
class NotAvailable(MadkhalError):
    """A generated artefact (results/*.json) does not exist yet."""


def _results(name: str) -> dict[str, Any]:
    p = paths.results_dir() / f"{name}.json"
    if not p.is_file():
        raise NotAvailable(f"results for {name.upper()} have not been generated; run madkhal eval")
    data: dict[str, Any] = read_json(p)
    return data


def policies_results() -> dict[str, Any]:
    from madkhal.lab.evaluation_report import predictions

    names = ("e1", "e2", "e3", "e4", "e5", "e6", "e7", "run")
    loaded = {n: _results(n) for n in names}
    out: dict[str, Any] = {n: loaded[n] for n in ("e1", "e2", "e3", "e4", "e5", "e6")}
    out["predictions"] = predictions(loaded)
    out["run"] = loaded["run"]
    return out


def replay(site: str) -> dict[str, Any]:
    check_site(site)
    e7 = _results("e7")
    return {"label": e7["label"], "draws": e7["draws"], "site": site, **e7["sites"][site]}


def _doc(name: str) -> str:
    p = paths.docs_dir() / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def method() -> dict[str, Any]:
    from madkhal.lab.evaluation_report import predictions

    try:
        preds = predictions({n: _results(n) for n in ("e1", "e2", "e3", "e4", "e5", "e6", "e7")})
    except NotAvailable:
        preds = []
    return {
        "scope": ADVISORY_SCOPE,
        "banner": {"evidence": BANNER_EVIDENCE, "hypothetical": BANNER_HYPOTHETICAL},
        "method_markdown": _doc("METHOD.md"),
        "limitations_markdown": _doc("LIMITATIONS.md"),
        "pilot_markdown": _doc("PILOT.md"),
        "parameters": plant_profile()["parameters"],
        "predictions": preds,
        "arabic_note": "The Arabic copy is machine drafted and should be reviewed by a native speaker.",
    }


def claims() -> dict[str, Any]:
    from madkhal.core.claims import load_claims

    rows = load_claims(paths.docs_dir() / "claims.yaml")
    return {
        "types": ["SOURCED", "SUPPORTED_BY_RESULT", "ASSUMPTION", "UNVERIFIED"],
        "claims": [
            {
                "id": c.id,
                "text": c.text,
                "type": c.type,
                "where": list(c.where),
                "pointer": {"kind": c.kind, "ref": c.ref},
            }
            for c in rows
        ],
    }


def provenance() -> dict[str, Any]:
    snap = snapshot()
    return {
        "app_version": __version__,
        "evidence": {
            "source_repository": snap.manifest["source_repository"],
            "source_commit": snap.manifest["source_commit"],
            "total_bytes": snap.manifest["total_bytes"],
            "files": [
                {"path": f["path"], "sha256": f["sha256"], "bytes": f["bytes"]}
                for f in snap.manifest["files"]
            ],
            "detectors": {d.value: snap.provenance(d) for d in (Dataset.olci_v1, Dataset.modis_v1)},
        },
        "ported_ideas": {
            "source_repository": "https://github.com/hudasol/dhill",
            "source_commit": "b751f002a6c61a599940c7ee932e533fbcfec627",
            "record": "docs/adr/0001-licence-and-scope.md",
        },
    }


def missions(
    site: str,
    date: str | None,
    radius_m: float,
    width_m: float,
    spacing_m: float,
    altitude_m: float,
    endurance_min: float,
    sortie_cost: float,
) -> dict[str, Any]:
    from madkhal.contract import DroneProfile
    from madkhal.tasking import MissionSpec, inspection_view

    check_site(site)
    day = parse_date(site, date)
    try:
        spec = MissionSpec(radius_m=radius_m, width_m=width_m, line_spacing_m=spacing_m)
    except ValueError as exc:
        raise InputError(str(exc)) from None
    drone = DroneProfile(altitude_m=altitude_m, endurance_min=endurance_min)
    return inspection_view(snapshot().site(site), day, spec, drone, sortie_cost)
