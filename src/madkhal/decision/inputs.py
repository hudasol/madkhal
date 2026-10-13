"""Decision inputs: everything an advisory depends on, storable and hashable."""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from madkhal.contract import Limits, PlantProfile, PlantState
from madkhal.core.jsonio import inputs_hash
from madkhal.estimator import AT_I, AT_V, CLEAR, DEV_I, DEV_V, Draws

HORIZON_DAYS_MAX = 8


@dataclass(frozen=True)
class DecisionInputs:
    """Belief per draw over (clear, developing, at_intake), the bloom transition rates per draw
    for the days of the horizon, the plant profile, its state, the limits and a seed."""

    site: str
    issued_for: dt.datetime
    belief: np.ndarray  # (D, 3)
    hazard: np.ndarray  # (D, days): daily onset probability from clear, per horizon day
    p_da: np.ndarray  # (D,)
    p_dc: np.ndarray  # (D,)
    p_ac: np.ndarray  # (D,)
    profile: PlantProfile
    state: PlantState
    limits: Limits
    seed: int = 7
    label: str = ""

    def __post_init__(self) -> None:
        d = self.belief.shape[0]
        if self.belief.ndim != 2 or self.belief.shape[1] != 3:
            raise ValueError("belief must have shape (D, 3)")
        if not np.allclose(self.belief.sum(axis=1), 1.0, atol=1e-9):
            raise ValueError("each belief row must sum to 1")
        if self.issued_for.tzinfo is None:
            raise ValueError("issued_for must be timezone aware (UTC)")
        for name in ("p_da", "p_dc", "p_ac"):
            if getattr(self, name).shape != (d,):
                raise ValueError(f"{name} must have shape (D,)")
        if self.hazard.shape[0] != d or self.hazard.shape[1] < self.horizon_days:
            raise ValueError("hazard must have shape (D, days covering the horizon)")

    @property
    def n_draws(self) -> int:
        return int(self.belief.shape[0])

    @property
    def horizon_days(self) -> int:
        return int(np.ceil(self.limits.horizon_hours / 24.0))

    def to_json(self) -> dict[str, Any]:
        return {
            "site": self.site,
            "issued_for": self.issued_for.astimezone(dt.UTC).isoformat(),
            "belief": self.belief.tolist(),
            "hazard": self.hazard.tolist(),
            "p_da": self.p_da.tolist(),
            "p_dc": self.p_dc.tolist(),
            "p_ac": self.p_ac.tolist(),
            "profile": self.profile.model_dump(mode="json"),
            "state": self.state.model_dump(mode="json"),
            "limits": self.limits.model_dump(mode="json"),
            "seed": self.seed,
            "label": self.label,
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> DecisionInputs:
        return DecisionInputs(
            site=str(data["site"]),
            issued_for=dt.datetime.fromisoformat(str(data["issued_for"])),
            belief=np.asarray(data["belief"], dtype=float),
            hazard=np.asarray(data["hazard"], dtype=float),
            p_da=np.asarray(data["p_da"], dtype=float),
            p_dc=np.asarray(data["p_dc"], dtype=float),
            p_ac=np.asarray(data["p_ac"], dtype=float),
            profile=PlantProfile.model_validate(data["profile"]),
            state=PlantState.model_validate(data["state"]),
            limits=Limits.model_validate(data["limits"]),
            seed=int(data["seed"]),
            label=str(data.get("label", "")),
        )

    def digest(self) -> str:
        """SHA-256 of the canonical inputs (arrays hashed by their exact bytes)."""
        arrays = {
            k: hashlib.sha256(
                np.ascontiguousarray(getattr(self, k), dtype=np.float64).tobytes()
            ).hexdigest()
            for k in ("belief", "hazard", "p_da", "p_dc", "p_ac")
        }
        scalars = {k: v for k, v in self.to_json().items() if k not in arrays}
        return inputs_hash({"arrays": arrays, "scalars": scalars})


def from_estimator(
    site: str,
    issued_for: dt.datetime,
    posterior: np.ndarray,
    draws: Draws,
    doy: int,
    profile: PlantProfile,
    state: PlantState,
    limits: Limits,
    seed: int = 7,
    label: str = "",
) -> DecisionInputs:
    """Build inputs from the estimator: ``posterior`` is the (D, 5) belief at the decision time."""
    b = np.stack(
        [
            posterior[:, CLEAR],
            posterior[:, DEV_V] + posterior[:, DEV_I],
            posterior[:, AT_V] + posterior[:, AT_I],
        ],
        axis=1,
    )
    b = b / b.sum(axis=1, keepdims=True)
    days = HORIZON_DAYS_MAX
    hazard = np.stack([draws.hazard((doy - 1 + k) % 365 + 1) for k in range(days)], axis=1)
    return DecisionInputs(
        site=site,
        issued_for=issued_for,
        belief=b,
        hazard=hazard,
        p_da=draws.p_da.copy(),
        p_dc=draws.p_dc.copy(),
        p_ac=draws.p_ac.copy(),
        profile=profile,
        state=state,
        limits=limits,
        seed=seed,
        label=label,
    )
