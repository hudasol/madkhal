# ADR 0008: Alarm discipline (dwell and hysteresis)

**Status:** accepted (P5), amended in P10 (see the end; the original text is kept).

## Context

Advisories that flap between actions create alarm floods and erode trust in a control room.
The brief asks for a minimum dwell of 12 hours before a less restrictive change, immediate
escalation, hysteresis and a measured change rate.

## Decision

1. **Dwell.** While the action in force has been held for less than `dwell_hours` (default 12),
   only candidates at least as restrictive as it are considered. Escalation to a more
   restrictive action is immediate. If no such candidate is feasible the advisory is
   NO_SAFE_OPTION_ESCALATE rather than an early relaxation (superseded in P10, see the
   amendment below).
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

## Amendment (P10, after the independent review)

The independent review showed that rule 1 could report NO_SAFE_OPTION_ESCALATE when a safe
option existed: within the dwell, if the action in force breaches a budget (for example a park
that runs storage dry), every feasible option is less restrictive and therefore blocked, and the
advice said "every option breaches", which was false. The brief asks for NO SAFE OPTION to be
shown when it is true.

Amended rule: dwell and hysteresis give way when they would leave no candidate although one
is within both budgets. That can only happen when the action in force and every more
restrictive option breach a budget. The advice then moves to the smallest relaxation within
budget (the most restrictive option that is within budget), its reasons say that the rules gave
way, and NO_SAFE_OPTION_ESCALATE is shown exactly when every option breaches a budget. A
property test checks that equivalence for every action in force, time in it and storage level.

Effect on rule 3: while the rules hold, they still depend only on the action in force and the
time in it, and the monotonicity properties hold (property tests, including within the
dwell). When they give way, a worse belief can move the advice from a restrictive option that
no longer meets its budget to a less restrictive one that does; this is the one stated
exception, and it is a move from a breaching option to one within budget.
