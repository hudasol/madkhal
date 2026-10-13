"""Sensitivity of the belief to the species blind spot assumption."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import numpy as np

from .filter import run_filter
from .params import PriorSpec, draw_parameters

# Beta(a, b) settings for the extra invisible share: none, the default, and a pessimistic one.
BLIND_SPOT_SETTINGS: tuple[tuple[str, float, float], ...] = (
    ("none", 1e-6, 1e6),
    ("default Beta(1, 4)", 1.0, 4.0),
    ("pessimistic Beta(2, 3)", 2.0, 3.0),
)


def blind_spot_runs(
    spec: PriorSpec,
    clear: Sequence[bool],
    alert: Sequence[bool],
    doy: Sequence[int],
    n_draws: int = 400,
    seed: int = 7,
    settings: Sequence[tuple[str, float, float]] = BLIND_SPOT_SETTINGS,
) -> list[dict[str, float | str]]:
    """Belief summaries under each blind spot setting (same evidence, same seed)."""
    c = np.asarray(clear, dtype=bool)
    a = np.asarray(alert, dtype=bool)
    quiet = c & ~a
    out: list[dict[str, float | str]] = []
    for label, ba, bb in settings:
        dr = draw_parameters(replace(spec, blind_spot_a=ba, blind_spot_b=bb), n_draws, seed)
        res = run_filter(c, a, doy, dr, horizons=(3,))
        any_med = np.median(1.0 - res.posterior[:, :, 0], axis=1)
        w3 = res.within[0]
        out.append(
            {
                "setting": label,
                "blind_mean": ba / (ba + bb),
                "mean_p_any_quiet_days": float(any_med[quiet].mean())
                if quiet.any()
                else float("nan"),
                "max_p_any": float(np.max(any_med)),
                "mean_width_within3": float(
                    np.mean(np.quantile(w3, 0.95, axis=1) - np.quantile(w3, 0.05, axis=1))
                ),
            }
        )
    return out
