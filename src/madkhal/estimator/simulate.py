"""Sample synthetic truth and detector observations from the estimator's own model.

Synthetic, for testing and for generator G1 only. Because the same model is used to
estimate, results on these samples are optimistic by construction (see G2 in the lab).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .filter import alert_likelihood, burn_in, propagate
from .params import AT_I, AT_V, CLEAR, DEV_I, DEV_V, N_STATES, Draws


@dataclass(frozen=True)
class Synthetic:
    """Synthetic days: hidden state (0 to 4), clear view and alert flags."""

    state: np.ndarray
    clear: np.ndarray
    alert: np.ndarray

    @property
    def at_intake(self) -> np.ndarray:
        out: np.ndarray = (self.state == AT_V) | (self.state == AT_I)
        return out

    @property
    def any_bloom(self) -> np.ndarray:
        out: np.ndarray = self.state != CLEAR
        return out

    def at_within(self, h: int) -> np.ndarray:
        """Truth of 'at the intake on any day from today to today + h'."""
        a = self.at_intake.astype(bool)
        out = a.copy()
        for k in range(1, h + 1):
            out[:-k] |= a[k:]
        return out


def sample_states(
    doy: Sequence[int] | np.ndarray, dr: Draws, rng: np.random.Generator
) -> np.ndarray:
    """Sample a hidden state path for a single draw (``dr.n`` must be 1)."""
    if dr.n != 1:
        raise ValueError("sample_states needs a single parameter draw")
    b = burn_in(int(doy[0]), dr)[0]
    s = int(rng.choice(N_STATES, p=b / b.sum()))
    out = np.empty(len(doy), dtype=int)
    for t, d in enumerate(doy):
        onehot = np.zeros((1, N_STATES))
        onehot[0, s] = 1.0
        p = propagate(onehot, int(d), dr)[0]
        s = int(rng.choice(N_STATES, p=p / p.sum()))
        out[t] = s
    return out


def observe(
    state: np.ndarray, clear_prob: np.ndarray, dr: Draws, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Clear view with probability ``clear_prob`` per day; alert from the likelihood."""
    lik = alert_likelihood(dr)[0]
    clear = rng.random(state.size) < clear_prob
    alert = clear & (rng.random(state.size) < lik[state])
    return clear, alert


def simulate(
    doy: Sequence[int] | np.ndarray, clear_prob: np.ndarray, dr: Draws, rng: np.random.Generator
) -> Synthetic:
    state = sample_states(doy, dr, rng)
    clear, alert = observe(state, np.asarray(clear_prob, float), dr, rng)
    return Synthetic(state=state, clear=clear, alert=alert)


__all__ = ["DEV_I", "DEV_V", "Synthetic", "observe", "sample_states", "simulate"]
