# ADR 0003: Bayesian bloom state filter with a visibility latent

**Status:** accepted (P3).

## Context

The question at the intake is "how likely is a bloom here now, and within the next few
days". The evidence is a daily detector output that is sometimes blind (no clear view),
sometimes wrong (false alarms), and sometimes structurally unable to see a bloom (the Al Raha
2023 diatom bloom produced no broadband anomaly).

## Decision

1. **Reported states.** Three: clear, developing (anomalous in the watch zone, not yet at the
   intake) and at_intake. Daily steps.
2. **Visibility latent.** Internally each bloom state is split into visible and invisible
   (five states). A new bloom is visible with probability `hit_rate * (1 - blind_spot)`.
   A visible bloom raises alerts at a high daily rate on clear days; an invisible bloom raises
   alerts only at the false alarm rate. Consequence: a long run of quiet clear days rules out
   visible blooms but cannot rule out an invisible one, which is the honest reading of the
   species blind spot.
3. **Transitions** (all ASSUMPTION, drawn per posterior draw with a lognormal spread of 0.4):
   onset hazard with a seasonal shape (peaks mid September and early February, the seasons of
   the dated events in Nadhir's results), developing to at_intake with median daily
   probability 0.2, developing to clear 0.1, at_intake to clear 1/14.
4. **Observations.** On a clear day the alert likelihoods are alpha (clear and invisible
   states), beta_dev and beta_at (visible states). beta_at and beta_dev are never below alpha.
5. **Parameter uncertainty is first class.** The filter runs forward over 400 posterior draws
   at once (vectorised). Every output is a median and a 90 percent equal tailed interval over
   draws.
6. **Forecast.** P(at the intake at any day from today to today + h) is computed by
   propagating the belief with the at_intake states made absorbing, for h = 1, 3 and 7.
7. **Start.** The belief on the first day is the propagation of "all clear" through 365 days
   with no data (a burn in), so that the series starts from the seasonal prior.

## Consequences

The filter is pure and deterministic for a given seed; its run time is measured in
`results/performance.json` (P10). It treats false alarm days as
conditionally independent given the state, although Nadhir's false alarms come in episodes;
the cluster correction of ADR 0005 widens alpha but does not remove this. A long false alarm
episode therefore raises the belief strongly. This is a stated limitation, and generator G2
tests clustered errors.
