# ADR 0008: Alarm discipline (dwell and hysteresis)

**Status:** accepted (P5).

## Context

Advisories that flap between actions create alarm floods and erode trust in a control room.
The brief asks for a minimum dwell of 12 hours before a less restrictive change, immediate
escalation, hysteresis and a measured change rate.

## Decision

1. **Dwell.** While the action in force has been held for less than `dwell_hours` (default 12),
   only candidates at least as restrictive as it are considered. Escalation to a more
   restrictive action is immediate. If no such candidate is feasible the advisory is
   NO_SAFE_OPTION_ESCALATE rather than an early relaxation.
2. **Hysteresis.** A candidate less restrictive than the action in force must meet both
   budgets with a margin of 0.8 (that is, at most 4 percent instead of 5 percent by default).
3. Both rules depend only on the action in force and the time in it, never on the belief, so
   they cannot break the monotonicity properties of ADR 0007.
4. **Change rate** is measured by the policy lab (E6) as changes per 30 days, together with
   dwell compliance.

## Consequences

In the daily replay the 12 hour dwell is never binding on its own (decisions are 24 hours
apart); the hysteresis margin does the work there, and the explanation records when it held a
more restrictive action (`dwell_held`). The dwell rule matters for the hourly scenario and API
use, where a caller passes the time in the current action.
