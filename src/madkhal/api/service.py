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
    BloomBelief,
    Dataset,
    Site,
    TrackRecord,
)
from madkhal.core.errors import InputError, UnknownSiteError
from madkhal.estimator import BeliefSeries
from madkhal.evidence import PINNED_COMMIT, RADII, monthly_clear_share, yearly_counts
from madkhal.lab.inputs import snapshot
from madkhal.lab.replay import belief_replay

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
