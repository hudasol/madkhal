"""Plain language rendering. The structured explanation is the source of truth; this text is
derived from it and never the other way round."""

from __future__ import annotations

from madkhal.contract import ActionKind, Explanation, PlainText


def _pct(x: float) -> str:
    return f"{100 * x:.1f} percent" if x < 0.1 else f"{100 * x:.0f} percent"


def render(
    action: ActionKind,
    scale: float,
    ex: Explanation,
    p_breach_full: float,
    time_to_limit_h: float | None,
) -> PlainText:
    any_bloom = ex.belief_summary.get("p_any_bloom_median", 0.0)
    lo = ex.belief_summary.get("p_any_bloom_lo", 0.0)
    hi = ex.belief_summary.get("p_any_bloom_hi", 0.0)
    if action == ActionKind.GO:
        what = "Run the intake at full scale."
    elif action == ActionKind.DERATE:
        what = f"Derate the intake to {round(100 * scale)} percent of full flow and apply the coagulant boost."
    elif action == ActionKind.PARK:
        what = "Park the intake (stop seawater intake) and serve demand from storage."
    else:
        what = "No safe option within the limits: escalate to the shift supervisor now."
    belief = f"The bloom belief in the watch zone is {_pct(any_bloom)} (90 percent interval {_pct(lo)} to {_pct(hi)})"
    full = f"at full scale the chance of reaching the fouling limit within {ex.limits.horizon_hours} hours is {_pct(p_breach_full)}"
    if time_to_limit_h is not None:
        full += f", with the limit reachable in about {time_to_limit_h:.0f} hours at the 95 percent risk quantile"
    binding = ex.binding_constraint.replace("_", " ") if ex.binding_constraint else "none"
    why = f"{belief}; {full}. Binding constraint: {binding}. Evidence level {ex.evidence_level.value}, {round(100 * ex.assumption_share)} percent of plant parameters are assumptions."
    if ex.dwell_held:
        why += " The dwell rule is holding a more restrictive action."
    change = (
        ex.what_would_change[0]
        if ex.what_would_change
        else "No change is expected from new evidence."
    )
    return PlainText(what=what, why=why, change=change)
