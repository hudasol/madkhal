"""Replay over real evidence: REPLAY: real satellite evidence, hypothetical plant.

The filter runs day by day over the real OLCI coverage and alerts. It is causal: the belief
on a day uses only evidence up to and including that day. No outcome of any real plant is
reported or implied.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from madkhal.contract import REPLAY_LABEL, Dataset
from madkhal.estimator import BeliefSeries, belief_series, draw_parameters
from madkhal.evidence import NadhirSnapshot

from .inputs import prior_spec, snapshot

REPLAY_SITES = ("kalba", "barka", "alraha")
OFFSETS_DAYS = (14, 7, 3)


@dataclass(frozen=True)
class ReplayPoint:
    event_id: str
    label: str
    status_badge: str
    anchor: str  # "t_ref" or "t_ref_earliest"
    anchor_date: dt.date
    days_before: int
    date: dt.date
    in_range: bool


def belief_replay(
    site: str, n_draws: int = 400, seed: int = 7, snap: NadhirSnapshot | None = None
) -> BeliefSeries:
    s = snap or snapshot()
    dr = draw_parameters(prior_spec(site, s), n_draws, seed)
    return belief_series(site, s.evidence_days(site), dr)


def event_points(site: str, snap: NadhirSnapshot | None = None) -> list[ReplayPoint]:
    """Dates 14, 7 and 3 days before each documented event's t_ref and t_ref_earliest."""
    s = snap or snapshot()
    days = s.evidence_days(site)
    first, last = days[0].date, days[-1].date
    out = []
    for e in s.events():
        if e.site != site or e.dataset != Dataset.olci_v1:
            continue
        for anchor, d0 in (("t_ref", e.t_ref), ("t_ref_earliest", e.t_ref_earliest)):
            if d0 is None:
                continue
            for k in OFFSETS_DAYS:
                d = d0 - dt.timedelta(days=k)
                out.append(
                    ReplayPoint(
                        event_id=e.id,
                        label=e.label,
                        status_badge=e.status_badge,
                        anchor=anchor,
                        anchor_date=d0,
                        days_before=k,
                        date=d,
                        in_range=first <= d <= last,
                    )
                )
    return out


def belief_at_events(site: str, n_draws: int = 400, seed: int = 7) -> dict[str, Any]:
    bs = belief_replay(site, n_draws, seed)
    rows = []
    for p in event_points(site):
        row: dict[str, Any] = {
            "event_id": p.event_id,
            "label": p.label,
            "status_badge": p.status_badge,
            "anchor": p.anchor,
            "anchor_date": p.anchor_date.isoformat(),
            "days_before": p.days_before,
            "date": p.date.isoformat(),
        }
        if p.in_range:
            i = bs.index_of(p.date)
            for name in ("any_bloom", "within_3"):
                lo, med, hi = (float(x) for x in bs.quantiles[name][i])
                row[name] = {"median": med, "lo": lo, "hi": hi}
            row["staleness_days"] = int(bs.staleness[i])
        else:
            row["note"] = "before the start of the satellite record"
        rows.append(row)
    return {"label": REPLAY_LABEL, "site": site, "points": rows}
