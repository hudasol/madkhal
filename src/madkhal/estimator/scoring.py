"""Proper scores and calibration summaries for probability forecasts."""

from __future__ import annotations

import numpy as np

EPS = 0.01  # probabilities are clipped to [EPS, 1 - EPS] for the log score


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def log_score(p: np.ndarray, y: np.ndarray) -> float:
    """Mean negative log likelihood (lower is better), probabilities clipped to [0.01, 0.99]."""
    q = np.clip(np.asarray(p, float), EPS, 1.0 - EPS)
    yy = np.asarray(y, float)
    return float(-np.mean(yy * np.log(q) + (1.0 - yy) * np.log(1.0 - q)))


def reliability(p: np.ndarray, y: np.ndarray, bins: int = 10) -> list[dict[str, float]]:
    """Observed frequency by forecast bin, with counts."""
    pp = np.asarray(p, float)
    yy = np.asarray(y, float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(pp, edges[1:-1]), 0, bins - 1)
    out = []
    for b in range(bins):
        m = idx == b
        n = int(m.sum())
        out.append(
            {
                "bin_lo": float(edges[b]),
                "bin_hi": float(edges[b + 1]),
                "n": float(n),
                "mean_forecast": float(pp[m].mean()) if n else float("nan"),
                "observed": float(yy[m].mean()) if n else float("nan"),
            }
        )
    return out


def interval_coverage(lo: np.ndarray, hi: np.ndarray, truth: np.ndarray) -> float:
    """Share of cases where the truth lies inside [lo, hi]."""
    t = np.asarray(truth, float)
    return float(np.mean((t >= np.asarray(lo)) & (t <= np.asarray(hi))))
