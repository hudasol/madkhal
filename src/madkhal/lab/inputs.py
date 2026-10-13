"""Bridge from the evidence layer to the estimator: priors built from Nadhir counts.

This is the only place where Nadhir numbers become estimator inputs. Every count is cited
to its snapshot file and row.
"""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from typing import Any

import numpy as np

from madkhal.contract import Dataset
from madkhal.estimator import PriorSpec
from madkhal.evidence import NadhirSnapshot, monthly_clear_share


@lru_cache(maxsize=1)
def snapshot() -> NadhirSnapshot:
    """The verified snapshot, loaded once per process."""
    return NadhirSnapshot()


def prior_spec(site: str, snap: NadhirSnapshot | None = None, **overrides: Any) -> PriorSpec:
    s = snap or snapshot()
    fa = {r.site: r for r in s.false_alarms(Dataset.olci_v1)}
    if site not in fa:
        raise KeyError(f"no held out false alarm counts for {site}")
    row = fa[site]
    tr = s.track_record()
    vis, vis_cite = s.detected_episode_alerts()
    hit_rows = [r for r in tr.rows if r.outcome != "NOT_OBSERVABLE"]
    spec = PriorSpec(
        site=site,
        alpha_alert_days=row.alert_days.k,
        alpha_clear_days=row.alert_days.n,
        alpha_episodes=row.episodes,
        hit_k=tr.hit_rate.k,
        hit_n=tr.hit_rate.n,
        vis_alert_k=vis.k,
        vis_alert_n=vis.n,
        citations={
            "alpha": f"{row.source_file} row {row.source_row}",
            "hit_rate": "; ".join(f"{r.source_file} row {r.source_row}" for r in hit_rows),
            "beta_at": vis_cite,
        },
    )
    return replace(spec, **overrides) if overrides else spec


def monthly_clear_prob(site: str, snap: NadhirSnapshot | None = None) -> np.ndarray:
    """Clear day share per calendar month (index 0 is January), from real coverage."""
    s = snap or snapshot()
    share = monthly_clear_share(s.evidence_days(site))
    return np.array([share[m].rate or 0.0 for m in range(1, 13)])
