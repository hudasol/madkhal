"""INSPECT: pre posterior value of a survey observation against its cost.

The value is computed for a Bayes decision maker with a linear loss (hypothetical cost units):
simulate each survey outcome, update the joint belief over draws and states, re decide by
minimum expected loss, and compare with the expected loss of deciding now. Because the expected
loss is linear in the joint belief, the value is never negative. INSPECT is set only when the
value times the weather availability exceeds the sortie cost; staleness alone never sets it.

The advised action itself still comes from the chance constrained rule (ADR 0007); the value of
information answers a separate question: is a look worth paying for (ADR 0010).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from madkhal.contract import ActionKind, InspectAssessment
from madkhal.estimator.survey import SurveySensor

from .inputs import DecisionInputs
from .risk import CANDIDATES, RiskTable


@dataclass(frozen=True)
class CostWeights:
    """Hypothetical cost units (CU). Used by the value of information and the policy lab."""

    forced_shutdown: float = 40_000.0
    cleaning: float = 10_000.0
    unserved_m3: float = 10.0
    membrane_index: float = 5_000.0
    derate_day: float = 500.0
    restart: float = 2_000.0

    def scaled(self, name: str, factor: float) -> CostWeights:
        return CostWeights(**{**self.__dict__, name: getattr(self, name) * factor})


@dataclass(frozen=True)
class SurveyConfig:
    sensor: SurveySensor = SurveySensor()
    availability: float = 0.8
    cost_cu: float = 1_000.0
    response_hours: float = 4.0


def loss_table(table: RiskTable, w: CostWeights) -> np.ndarray:
    """Loss per draw, start state and candidate, shape (D, 3, K)."""
    k_n = len(CANDIDATES)
    derate = np.array([1.0 if a == ActionKind.DERATE else 0.0 for a, _ in CANDIDATES])
    park = np.array([1.0 if a == ActionKind.PARK else 0.0 for a, _ in CANDIDATES])
    days = 3.0  # the horizon covers about three daily decisions
    loss: np.ndarray = (
        table.fouling_breach * (w.forced_shutdown + w.cleaning)
        + table.unserved_m3 * w.unserved_m3
        + (derate * w.derate_day * days + park * w.restart).reshape(1, 1, k_n)
    )
    return loss


def _bayes(loss: np.ndarray, weights: np.ndarray, prefer: int) -> tuple[int, float]:
    """Index and value of the minimum expected loss; ties go to ``prefer``."""
    exp = np.einsum("ds,dsk->k", weights, loss)
    best = int(np.argmin(exp))
    if exp[prefer] <= exp[best] + 1e-9:
        best = prefer
    return best, float(exp[best])


def value_of_information(
    inp: DecisionInputs, table: RiskTable, cfg: SurveyConfig, w: CostWeights | None = None
) -> tuple[float, bool]:
    """Expected loss reduction from one survey (before weather), and whether any outcome
    changes the Bayes action."""
    loss = loss_table(table, w or CostWeights())
    b = inp.belief
    joint = b / b.shape[0]  # joint weights over (draw, state); sums to 1
    a0, l0 = _bayes(loss, joint, prefer=0)
    a0, l0 = _bayes(loss, joint, prefer=a0)
    total = 0.0
    changes = False
    for detected in (True, False):
        lik = cfg.sensor.likelihood3(detected)
        post = joint * lik[None, :]
        p_y = float(post.sum())
        if p_y <= 0.0:
            continue
        ay, ly = _bayes(loss, post / p_y, prefer=a0)
        total += p_y * ly
        changes = changes or ay != a0
    raw = l0 - total
    if raw < -1e-6 * max(1.0, abs(l0)):
        raise ArithmeticError(f"negative value of information {raw}; the loss must be linear")
    return max(0.0, raw), changes


def assess(
    inp: DecisionInputs, table: RiskTable, cfg: SurveyConfig, w: CostWeights | None = None
) -> InspectAssessment:
    voi, changes = value_of_information(inp, table, cfg, w)
    value = cfg.availability * voi
    inspect = value > cfg.cost_cu
    reasons = [
        f"Expected value of one survey: {value:,.0f} CU after weather availability "
        f"{cfg.availability:.0%}; sortie cost {cfg.cost_cu:,.0f} CU (hypothetical units)."
    ]
    if inspect:
        reasons.append("The survey pays for itself: a result could change the best action.")
    elif not changes:
        reasons.append("No survey result would change the best action, so a survey would not pay.")
    else:
        reasons.append(
            "A survey could change the action, but its expected value is below its cost."
        )
    return InspectAssessment(
        value_cu=value,
        sortie_cost_cu=cfg.cost_cu,
        break_even_cost_cu=value,
        availability=cfg.availability,
        decision_could_change=changes,
        inspect=inspect,
        reasons=reasons,
    )
