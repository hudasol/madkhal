# ADR 0007: Decision feasibility rule, built to be monotone in bad news

**Status:** accepted (P5).

## Context

The engineering lens asks that an advisory never becomes more permissive because the evidence
got worse, and the brief asks for property tests that prove it for four kinds of bad news: a
higher bloom probability, wider plant parameter spreads, a tighter risk budget and lower
storage. A plain Monte Carlo over parameters does not guarantee these properties, so they are
built into the rule.

## Decision

1. **Candidates.** GO (q = 1), DERATE with q from 0.9 to 0.2 in steps of 0.1 with the coagulant
   boost, and PARK (q = 0).
2. **Risk table.** For every posterior draw d, start state s in (clear, developing, at_intake)
   and candidate k, one bloom path and one plant are simulated hourly over the horizon
   (default 72 hours) with common random numbers: the same bloom path uniforms, the same Pareto
   bloom load and the same plant parameters for every s and k of a draw. Recorded: fouling
   breach, unserved water above the allowance, unserved volume and breach hour.
3. **Monotone in the start state.** The table is replaced by its cumulative maximum across
   clear, developing, at_intake (cumulative minimum for the breach hour). This can only raise
   risk, and it makes a more severe start state never safer.
4. **Linear in the belief.** P(fouling breach) and P(water shortfall) for a candidate are the
   belief weighted means of the table: mean over d of the sum over s of b(d, s) times the table
   entry. Moving belief mass towards more severe states therefore can never lower them.
5. **Feasible.** Both probabilities within budget (default 5 percent each). The most permissive
   feasible candidate is chosen. If none is feasible: NO_SAFE_OPTION_ESCALATE, with the least
   bad option named in the reasons.
6. **Parameter uncertainty resolved against the operator.** Physics parameters (pretreatment
   capacity, coagulant boost, background and bloom load, tail index, fouling rate) are sampled as
   value times exp(spread times max(z, 0)) in their adverse direction: half the draws stay at
   the nominal value and the other half move towards the adverse side. A wider spread therefore
   moves every draw weakly towards the adverse side, and because the simulator is monotone in
   each adverse parameter (fouling up to the hard limit, breach time, and, with the decision mode
   rule below, unserved water), a wider spread can never make a candidate safer.
   Operating quantities that an operator knows at decision time (design flow, demand, storage
   capacity) are used at their value; their spreads matter only for the hidden plants of the
   policy lab.
7. **Decision mode.** Inside the horizon a lane that reaches the fouling limit stays offline for
   the rest of the horizon. An earlier breach is then never better for water security, which
   keeps unserved water monotone in every adverse parameter. This is conservative; the lab
   simulates the full dynamics (cleaning, restart).
8. **Time to limit** is the earliest hour by which P(breach at full scale) reaches 5 percent
   (the 95 percent risk quantile), or absent when that does not happen within the horizon.

## Consequences

The four safety properties hold by construction and are checked with hypothesis property tests
(`tests/test_decision.py`). The price is conservatism: with every plant parameter an assumption
(evidence level L0), the adverse half of the draws costs flow. Calibration (L2) shrinks the
spreads and directly relaxes the advice; the policy lab measures the price (E2, E3).

A subtlety recorded here: total fouling dose is not monotone in load, because a higher load
trips the plant earlier and no breakthrough accrues afterwards. The monotone quantities are the
fouling index up to the hard limit and the breach time, and those are what the tests check.
