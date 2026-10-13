"""Coverage aware Bayesian bloom state filter (forward algorithm over parameter draws).

Each day: propagate the belief with the seasonal transition model, then, only if the
satellite had a clear view, multiply by the likelihood of the alert value. A nodata day
skips the update entirely: it carries no information, so the belief is the propagated
prior. All arithmetic is vectorised over the posterior draws.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .params import AT_I, AT_V, CLEAR, DEV_I, DEV_V, N_STATES, Draws

HORIZONS = (1, 3, 7)

Flags = Sequence[bool] | np.ndarray
Days = Sequence[int] | np.ndarray


def initial_belief(n_draws: int) -> np.ndarray:
    b = np.zeros((n_draws, N_STATES))
    b[:, CLEAR] = 1.0
    return b


def propagate(b: np.ndarray, doy: int, dr: Draws) -> np.ndarray:
    """One day of the transition model for every draw. ``b`` has shape (D, 5)."""
    lam = dr.hazard(doy)
    v = dr.visible_share
    stay_dev = 1.0 - dr.p_da - dr.p_dc
    stay_at = 1.0 - dr.p_ac
    out = np.empty_like(b)
    out[:, CLEAR] = (
        b[:, CLEAR] * (1.0 - lam)
        + (b[:, DEV_V] + b[:, DEV_I]) * dr.p_dc
        + (b[:, AT_V] + b[:, AT_I]) * dr.p_ac
    )
    out[:, DEV_V] = b[:, CLEAR] * lam * v + b[:, DEV_V] * stay_dev
    out[:, DEV_I] = b[:, CLEAR] * lam * (1.0 - v) + b[:, DEV_I] * stay_dev
    out[:, AT_V] = b[:, DEV_V] * dr.p_da + b[:, AT_V] * stay_at
    out[:, AT_I] = b[:, DEV_I] * dr.p_da + b[:, AT_I] * stay_at
    return out


def alert_likelihood(dr: Draws) -> np.ndarray:
    """P(alert | state) on a clear day, shape (D, 5)."""
    lik = np.empty((dr.n, N_STATES))
    lik[:, CLEAR] = dr.alpha
    lik[:, DEV_V] = dr.beta_dev
    lik[:, DEV_I] = dr.alpha
    lik[:, AT_V] = dr.beta_at
    lik[:, AT_I] = dr.alpha
    return lik


def update(b: np.ndarray, clear: bool, alert: bool, dr: Draws) -> np.ndarray:
    """Observation update. A nodata day returns ``b`` unchanged."""
    if not clear:
        return b
    lik = alert_likelihood(dr)
    if not alert:
        lik = 1.0 - lik
    post = b * lik
    out: np.ndarray = post / post.sum(axis=1, keepdims=True)
    return out


def next_doy(doy: int, k: int) -> int:
    return (doy - 1 + k) % 365 + 1


def p_at_within(b: np.ndarray, doy: int, horizons: Sequence[int], dr: Draws) -> np.ndarray:
    """P(at the intake at any day from today to today + h), shape (len(horizons), D)."""
    hmax = max(horizons) if horizons else 0
    p = b[:, AT_V] + b[:, AT_I]
    v = b.copy()
    v[:, AT_V] = 0.0
    v[:, AT_I] = 0.0
    acc = {0: p.copy()}
    for k in range(1, hmax + 1):
        v = propagate(v, next_doy(doy, k), dr)
        p = p + v[:, AT_V] + v[:, AT_I]
        v[:, AT_V] = 0.0
        v[:, AT_I] = 0.0
        acc[k] = p.copy()
    return np.stack([acc[h] for h in horizons]) if horizons else np.zeros((0, dr.n))


def burn_in(doy_first: int, dr: Draws, days: int = 365) -> np.ndarray:
    """Belief on the day before ``doy_first`` after ``days`` days with no data from all clear."""
    b = initial_belief(dr.n)
    for k in range(days, 0, -1):
        b = propagate(b, next_doy(doy_first, -k), dr)
    return b


@dataclass(frozen=True)
class FilterResult:
    """Filter output for consecutive days."""

    posterior: np.ndarray  # (T, D, 5), belief at the end of each day
    within: np.ndarray  # (H, T, D)
    horizons: tuple[int, ...]
    staleness: np.ndarray  # (T,), -1 when no clear day yet

    def marginals(self) -> dict[str, np.ndarray]:
        p = self.posterior
        return {
            "clear": p[:, :, CLEAR],
            "developing": p[:, :, DEV_V] + p[:, :, DEV_I],
            "at_intake": p[:, :, AT_V] + p[:, :, AT_I],
            "any_bloom": 1.0 - p[:, :, CLEAR],
        }


def run_filter(
    clear: Flags,
    alert: Flags,
    doy: Days,
    dr: Draws,
    horizons: Sequence[int] = HORIZONS,
    init: np.ndarray | None = None,
    staleness_start: int = -1,
) -> FilterResult:
    """Run the filter over consecutive days. Pure: same inputs give identical outputs."""
    t_n = len(doy)
    if not (len(clear) == len(alert) == t_n):
        raise ValueError("clear, alert and doy must have the same length")
    if t_n == 0:
        raise ValueError("at least one day is required")
    b = burn_in(int(doy[0]), dr) if init is None else init.copy()
    post = np.empty((t_n, dr.n, N_STATES))
    within = np.empty((len(horizons), t_n, dr.n))
    stale = np.empty(t_n, dtype=int)
    last = staleness_start
    for t in range(t_n):
        b = propagate(b, int(doy[t]), dr)
        if alert[t] and not clear[t]:
            raise ValueError(f"day {t}: an alert requires a clear view")
        b = update(b, bool(clear[t]), bool(alert[t]), dr)
        post[t] = b
        within[:, t, :] = p_at_within(b, int(doy[t]), horizons, dr)
        if clear[t]:
            last = 0
        elif last >= 0:
            last += 1
        stale[t] = last
    return FilterResult(posterior=post, within=within, horizons=tuple(horizons), staleness=stale)


def seasonal_prior(
    doy: Sequence[int], dr: Draws, horizons: Sequence[int] = HORIZONS
) -> FilterResult:
    """The belief with no observations at all (every day nodata)."""
    n = len(doy)
    return run_filter([False] * n, [False] * n, doy, dr, horizons)
