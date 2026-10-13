# ADR 0010: INSPECT by pre posterior value of information

**Status:** accepted (P6, used by P8).

## Context

A survey drone can look at the water near the intake. Sending it costs money and crew time. The
brief asks that INSPECT is advised only when a look pays for itself, never merely because the
satellite evidence is old.

## Decision

1. **Sensor (ASSUMPTION).** P(survey reports a bloom | clear) 0.05, | developing 0.6, | at the
   intake 0.9, the same whether or not the satellite can see the bloom. Weather availability is
   a probability; a sortie has a cost in hypothetical cost units (CU).
2. **Loss (hypothetical CU).** Per draw and start state, the loss of a candidate action is
   (forced shutdown plus cleaning) times P(breach), plus unserved water times its weight, plus a
   coagulant cost for derate days and a restart cost for PARK, from the same risk table as the
   decision.
3. **Value.** For each survey outcome, the joint belief over draws and states is updated, the
   Bayes action (minimum expected loss) is recomputed, and the expected loss after the survey is
   compared with the expected loss now. Because the expected loss is linear in the joint
   belief, the value is never negative; the code raises an error if it ever is.
4. **Rule.** INSPECT is set when availability times value exceeds the sortie cost. The break
   even sortie cost reported is availability times value. Ties in the Bayes action go to the
   action chosen now, so with a perfect free sensor INSPECT is set exactly when some outcome
   would change the action.
5. **Separation.** The advised action still comes from the chance constrained rule of ADR 0007.
   The value of information answers a different question (is a look worth paying for) with an
   economic loss. The two can disagree; both are shown in the explanation.

## Consequences

Staleness does not enter the value directly: only the belief does. Long blind spells raise the
value only through the belief they produce. E4 measures when INSPECT pays across weather
availability and sortie cost.
