"""Merge a drone survey result into the belief (an observation update).

The survey sensor is an ASSUMPTION (see docs/PARAMETERS.md and ADR 0010): its detection
probability depends on the bloom state but not on whether the satellite can see the bloom, so
a survey can reveal a bloom that the broadband detector is blind to.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .params import AT_I, AT_V, CLEAR, DEV_I, DEV_V, N_STATES


@dataclass(frozen=True)
class SurveySensor:
    """P(survey reports a bloom | state) for clear, developing and at the intake."""

    p_clear: float = 0.05
    p_developing: float = 0.6
    p_at_intake: float = 0.9

    def __post_init__(self) -> None:
        for v in (self.p_clear, self.p_developing, self.p_at_intake):
            if not 0.0 <= v <= 1.0:
                raise ValueError("survey probabilities must be in [0, 1]")

    def likelihood5(self, detected: bool) -> np.ndarray:
        lik = np.empty(N_STATES)
        lik[CLEAR] = self.p_clear
        lik[DEV_V] = lik[DEV_I] = self.p_developing
        lik[AT_V] = lik[AT_I] = self.p_at_intake
        out: np.ndarray = lik if detected else 1.0 - lik
        return out

    def likelihood3(self, detected: bool) -> np.ndarray:
        lik = np.array([self.p_clear, self.p_developing, self.p_at_intake])
        out: np.ndarray = lik if detected else 1.0 - lik
        return out


def survey_update(b: np.ndarray, detected: bool, sensor: SurveySensor) -> np.ndarray:
    """Posterior belief per draw, shape (D, 5), after a survey result."""
    post = b * sensor.likelihood5(detected)[None, :]
    z = post.sum(axis=1, keepdims=True)
    out: np.ndarray = np.where(z > 0, post / np.where(z > 0, z, 1.0), b)
    return out
