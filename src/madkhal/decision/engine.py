"""Decision engine: GO, DERATE, PARK or NO_SAFE_OPTION_ESCALATE, with reasons.

A candidate is feasible when, over the horizon and the joint posterior (bloom state and
parameters), P(fouling breach) <= the fouling budget and P(unserved water above the allowance)
<= the water budget. The most permissive feasible candidate is chosen. Alarm discipline:

* dwell: within ``dwell_hours`` of the last change only candidates at least as restrictive as
  the action in force are considered (escalation stays immediate);
* hysteresis: a candidate less restrictive than the action in force must meet the budgets with
  a margin (``RELAX_MARGIN`` times the budget).

Both rules depend only on the action in force, never on the belief, so a higher bloom
probability, wider plant spreads, a tighter budget or lower storage can never make the advice
more permissive (property tests in tests/test_decision.py).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

from madkhal.contract import (
    ActionKind,
    Advisory,
    CandidateEvaluation,
    ConstraintStatus,
    Explanation,
    InspectAssessment,
    restrictiveness,
)

from .explain import render
from .inputs import DecisionInputs
from .risk import CANDIDATES, RiskTable, risk_table, time_to_limit

RELAX_MARGIN = 0.8


@dataclass(frozen=True)
class Evaluation:
    table: RiskTable
    p_foul: np.ndarray
    p_water: np.ndarray
    unserved: np.ndarray
    feasible: np.ndarray  # under the rule that applies to each candidate
    allowed: np.ndarray  # dwell restriction
    choice: int | None  # index into CANDIDATES, None means no safe option
    unconstrained: int | None


def evaluate(inp: DecisionInputs, table: RiskTable | None = None) -> Evaluation:
    tb = table if table is not None else risk_table(inp)
    b = inp.belief
    p_foul = tb.weighted(b, "fouling_breach")
    p_water = tb.weighted(b, "water_breach")
    unserved = tb.weighted(b, "unserved_m3")
    lim = inp.limits
    cur = restrictiveness(inp.state.current_action, inp.state.current_scale)
    rest = np.array([restrictiveness(a, q) for a, q in CANDIDATES])
    relaxing = rest < cur - 1e-12
    margin = np.where(relaxing, RELAX_MARGIN, 1.0)
    feasible = (p_foul <= lim.fouling_risk_budget * margin + 1e-12) & (
        p_water <= lim.water_risk_budget * margin + 1e-12
    )
    plain = (p_foul <= lim.fouling_risk_budget + 1e-12) & (p_water <= lim.water_risk_budget + 1e-12)
    in_dwell = inp.state.hours_in_action < lim.dwell_hours
    allowed = ~relaxing if in_dwell else np.ones(len(CANDIDATES), dtype=bool)
    ok = np.flatnonzero(feasible & allowed)
    unc = np.flatnonzero(plain)
    return Evaluation(
        table=tb,
        p_foul=p_foul,
        p_water=p_water,
        unserved=unserved,
        feasible=feasible,
        allowed=allowed,
        choice=int(ok[0]) if ok.size else None,
        unconstrained=int(unc[0]) if unc.size else None,
    )


def _violations(ev: Evaluation, k: int, inp: DecisionInputs) -> list[str]:
    lim = inp.limits
    out = []
    if ev.p_foul[k] > lim.fouling_risk_budget + 1e-12:
        out.append("fouling")
    if ev.p_water[k] > lim.water_risk_budget + 1e-12:
        out.append("water_security")
    if not ev.allowed[k]:
        out.append("dwell")
    if not out and not ev.feasible[k]:
        out.append("hysteresis")
    return out


def _used(value: float, budget: float) -> float:
    if budget <= 0:
        return 100.0 if value > 0 else 0.0
    return float(min(100.0, 100.0 * value / budget))


def decide(inp: DecisionInputs, inspect: InspectAssessment | None = None) -> Advisory:
    """The advisory for one site and time. Pure: same inputs give the same advisory."""
    ev = evaluate(inp)
    lim = inp.limits
    k = ev.choice
    if k is None:
        action, scale = ActionKind.NO_SAFE_OPTION_ESCALATE, 0.0
    else:
        action, scale = CANDIDATES[k]
    # binding constraint: why not the next more permissive candidate
    binding: str | None
    if k is None:
        names = sorted({v for j in range(len(CANDIDATES)) for v in _violations(ev, j, inp)})
        binding = " and ".join(names) if names else None
    elif k == 0:
        binding = (
            "fouling"
            if ev.p_foul[0] / max(lim.fouling_risk_budget, 1e-12)
            >= ev.p_water[0] / max(lim.water_risk_budget, 1e-12)
            else "water_security"
        )
    else:
        v = _violations(ev, k - 1, inp)
        binding = " and ".join(v) if v else None
    ref = k if k is not None else len(CANDIDATES) - 1
    constraints = [
        ConstraintStatus(
            name="fouling",
            value=float(ev.p_foul[ref]),
            budget=lim.fouling_risk_budget,
            used_percent=_used(float(ev.p_foul[ref]), lim.fouling_risk_budget),
        ),
        ConstraintStatus(
            name="water_security",
            value=float(ev.p_water[ref]),
            budget=lim.water_risk_budget,
            used_percent=_used(float(ev.p_water[ref]), lim.water_risk_budget),
        ),
        ConstraintStatus(
            name="dwell",
            value=float(min(inp.state.hours_in_action, lim.dwell_hours)),
            budget=lim.dwell_hours,
            used_percent=_used(
                float(min(inp.state.hours_in_action, lim.dwell_hours)), lim.dwell_hours
            ),
        ),
    ]
    candidates = [
        CandidateEvaluation(
            action=a,
            scale=q,
            p_fouling_breach=float(np.clip(ev.p_foul[j], 0, 1)),
            p_water_breach=float(np.clip(ev.p_water[j], 0, 1)),
            expected_unserved_m3=float(max(ev.unserved[j], 0.0)),
            feasible=bool(ev.feasible[j] and ev.allowed[j]),
        )
        for j, (a, q) in enumerate(CANDIDATES)
    ]
    b = inp.belief
    belief_summary = {
        "p_clear_median": float(np.median(b[:, 0])),
        "p_developing_median": float(np.median(b[:, 1])),
        "p_at_intake_median": float(np.median(b[:, 2])),
        "p_any_bloom_median": float(np.median(1.0 - b[:, 0])),
        "p_any_bloom_lo": float(np.quantile(1.0 - b[:, 0], 0.05)),
        "p_any_bloom_hi": float(np.quantile(1.0 - b[:, 0], 0.95)),
    }
    unc = ev.unconstrained
    unc_action, unc_scale = (
        CANDIDATES[unc] if unc is not None else (ActionKind.NO_SAFE_OPTION_ESCALATE, 0.0)
    )
    held = bool(
        k is not None
        and unc is not None
        and restrictiveness(action, scale) > restrictiveness(unc_action, unc_scale) + 1e-12
    )
    profile = inp.profile
    what_change = _what_would_change(ev, k, inp)
    explanation = Explanation(
        belief_summary=belief_summary,
        plant_state=inp.state,
        limits=lim,
        candidates=candidates,
        unconstrained_action=unc_action,
        unconstrained_scale=unc_scale,
        dwell_held=held,
        binding_constraint=binding,
        evidence_level=profile.evidence_level,
        assumption_share=profile.assumption_share,
        n_samples=inp.n_draws,
        inspect=inspect,
        what_would_change=what_change,
    )
    t_limit = time_to_limit(ev.table, b, 0)
    reasons = _reasons(ev, k, inp, binding)
    text = render(action, scale, explanation, float(ev.p_foul[0]), t_limit)
    digest = inp.digest()
    return Advisory(
        id=digest[:16],
        site=inp.site,
        issued_for=inp.issued_for.astimezone(dt.UTC),
        action=action,
        scale=scale,
        reasons=reasons,
        binding_constraint=binding,
        p_breach_full_scale=float(np.clip(ev.p_foul[0], 0, 1)),
        time_to_limit_hours=t_limit,
        constraints=constraints,
        evidence_level=profile.evidence_level,
        assumption_share=profile.assumption_share,
        inspect=bool(inspect.inspect) if inspect else False,
        inspect_reasons=list(inspect.reasons) if inspect else ["Survey value not assessed."],
        explanation=explanation,
        text=text,
        inputs_hash=digest,
        seed=inp.seed,
        label=inp.label,
    )


def _pct(x: float) -> str:
    return f"{100 * x:.1f} percent" if x < 0.1 else f"{100 * x:.0f} percent"


def _reasons(ev: Evaluation, k: int | None, inp: DecisionInputs, binding: str | None) -> list[str]:
    lim = inp.limits
    out = []
    if k is None:
        out.append(
            "No candidate keeps both risks within budget: every option breaches the fouling limit "
            "or runs out of stored water within the horizon."
        )
        best = int(
            np.argmin(
                np.maximum(ev.p_foul / lim.fouling_risk_budget, ev.p_water / lim.water_risk_budget)
            )
        )
        a, q = CANDIDATES[best]
        out.append(
            f"Least bad option: {a.value} at scale {q:.1f} (P(fouling breach) {_pct(float(ev.p_foul[best]))}, "
            f"P(water shortfall) {_pct(float(ev.p_water[best]))})."
        )
        return out
    a, q = CANDIDATES[k]
    out.append(
        f"P(fouling breach) {_pct(float(ev.p_foul[k]))} against a budget of {_pct(lim.fouling_risk_budget)}; "
        f"P(water shortfall) {_pct(float(ev.p_water[k]))} against {_pct(lim.water_risk_budget)}."
    )
    if k > 0 and binding:
        pa, pq = CANDIDATES[k - 1]
        out.append(
            f"The next more permissive option ({pa.value} at {pq:.1f}) is limited by {binding.replace('_', ' ')}."
        )
    if k == 0:
        out.append("Full scale operation keeps both risks within budget.")
    return out


def _what_would_change(ev: Evaluation, k: int | None, inp: DecisionInputs) -> list[str]:
    lim = inp.limits
    out = []
    if k is None or k > 0:
        out.append(
            f"Full scale becomes acceptable when P(fouling breach) at full scale falls to "
            f"{_pct(lim.fouling_risk_budget)} or less; it is {_pct(float(ev.p_foul[0]))} now."
        )
    if k is not None and k < len(CANDIDATES) - 1 and ev.p_foul[k] > 0:
        out.append(
            "A satellite alert, or a confirmed bloom at the intake, would push towards a lower scale."
        )
    out.append(
        "A clear satellite view with no alert would lower the bloom belief for visible blooms."
    )
    if any(ev.p_water > lim.water_risk_budget):
        out.append("More stored water would widen the set of options that keep supply secure.")
    if inp.state.hours_in_action < lim.dwell_hours:
        out.append(
            f"The dwell rule holds the current action until {lim.dwell_hours:g} hours have passed "
            f"({inp.state.hours_in_action:g} so far)."
        )
    return out
