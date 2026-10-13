"""Baseline estimators the filter is compared with (E1)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

Flags = Sequence[bool] | np.ndarray


def alert_means_bloom(alert: Flags) -> np.ndarray:
    """Probability 1 of a bloom at the intake on an alert day, 0 otherwise."""
    return np.asarray(alert, dtype=float)


def persistence(alert: Flags, hold_days: int = 7) -> np.ndarray:
    """Probability 1 for ``hold_days`` days after any alert (today included), 0 otherwise."""
    if hold_days < 1:
        raise ValueError("hold_days must be at least 1")
    a = np.asarray(alert, dtype=bool)
    out = np.zeros(a.size)
    last = -(10**9)
    for t in range(a.size):
        if a[t]:
            last = t
        out[t] = 1.0 if t - last < hold_days else 0.0
    return out
