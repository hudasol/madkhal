"""E1 smoke run: one synthetic year from the estimator's own model, scored quickly.

Synthetic data. This only checks that the estimator, the baselines and the scores run end
to end; the preregistered E1 runs many seeds on generator G1 (see docs/PREREGISTRATION.md).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np

from madkhal.core.determinism import substream
from madkhal.estimator import (
    alert_means_bloom,
    brier,
    draw_parameters,
    log_score,
    persistence,
    run_filter,
    simulate,
)

from .inputs import monthly_clear_prob, prior_spec


def e1_smoke(
    seed: int = 1, site: str = "kalba", days: int = 365, n_draws: int = 100
) -> dict[str, Any]:
    spec = prior_spec(site)
    truth_draws = draw_parameters(spec, n_draws, seed).posterior_mean()
    start = dt.date(2021, 1, 1)
    dates = [start + dt.timedelta(days=k) for k in range(days)]
    doy = [d.timetuple().tm_yday for d in dates]
    cp = monthly_clear_prob(site)[[d.month - 1 for d in dates]]
    syn = simulate(doy, cp, truth_draws, substream(seed, "smoke.truth"))
    dr = draw_parameters(spec, n_draws, seed + 1000)
    res = run_filter(syn.clear, syn.alert, doy, dr, horizons=(3,))
    p_filter = np.median(res.within[0], axis=1)
    y = syn.at_within(3).astype(float)
    return {
        "label": "SYNTHETIC smoke run (one seed, one year); not a result",
        "site_coverage_from": site,
        "days": days,
        "bloom_days_at_intake": int(syn.at_intake.sum()),
        "clear_days": int(syn.clear.sum()),
        "alert_days": int(syn.alert.sum()),
        "brier": {
            "madkhal": brier(p_filter, y),
            "alert_means_bloom": brier(alert_means_bloom(syn.alert), y),
            "persistence": brier(persistence(syn.alert, 7), y),
        },
        "log_score": {
            "madkhal": log_score(p_filter, y),
            "alert_means_bloom": log_score(alert_means_bloom(syn.alert), y),
            "persistence": log_score(persistence(syn.alert, 7), y),
        },
    }
