# Preregistration

Written and committed before any experiment result exists (phase P6, 2026-10-13). After the
runs, every prediction below is marked HIT or MISS in `docs/EVALUATION.md`, misses included.
Changes to this design after results exist are allowed only as dated amendments at the end of
this file, keeping the original text.

## Disclosures

* **Who built the worlds.** Generators G1 and G2 are written by the same author as the
  estimator and the decision engine. G1 deliberately shares the estimator's assumptions
  (structure, seasonal shape, transition rates, detector rates at their posterior means), so
  results on G1 are optimistic by construction. G2 exists to break those assumptions.
* **What was already seen.** During development, before this file: (a) one E1 smoke run on a
  development seed (seed 1, one synthetic year), where the filter's Brier score was lower than
  both baselines; (b) the P5 replay of Kalba over September 2018, where the advice moved from
  GO to DERATE on 8 September 2018. Predictions about Kalba 2018 in E7 are therefore not blind.
* **Seeds.** Development and debugging use seeds below 1000. Evaluation seeds are 1000 to 1029
  (30 seeds) unless an experiment states otherwise. No parameter of the method is tuned on
  evaluation seeds. The method's own settings (priors, plant profile, budgets, dwell, margin)
  were fixed in P3 and P5 and are not changed for evaluation.
* **Budget.** The suite must run in under 15 minutes on the development laptop (16 cores). If
  it does not, seeds are reduced to 20 for the affected experiments and the reduction is
  recorded as an amendment.

## Common design

* **Unit of simulation.** One run is one seed of a generator over 2 synthetic years (730 days,
  calendar 2021 to 2022 for seasonality only), with Kalba's real monthly clear sky shares from
  the Nadhir snapshot and Kalba's estimator priors.
* **Hidden truth plant.** Per seed, the physics parameters of the plant profile are drawn
  two sided (lognormal, the profile's spreads); operating quantities (design flow, demand,
  storage capacity) are at their values and known to every policy. Initial fouling 0.2,
  initial storage 24 hours of demand. The lab simulates full dynamics: forced cleaning with
  restart, restart after PARK, and a planned cleaning when fouling reaches 0.6.
* **Bloom load.** Each continuous bloom episode at the intake gets one Pareto load from the
  truth plant's lower bound and tail index.
* **Decisions.** Daily at 06:00 local time; the action applies for the next 24 hours. Madkhal
  policies use the estimator with 100 parameter draws (seed 7; the replay uses 400) and the
  decision engine with default limits (72 hour horizon, 5 percent budgets, 12 hour dwell, 0.8
  hysteresis margin). Risk tables are cached by day of year and by the plant state rounded
  conservatively (fouling rounded up to 0.05, storage rounded down to 2 hours). When the engine
  returns NO_SAFE_OPTION_ESCALATE, the simulated operator applies the least bad candidate and
  the day is counted as an escalation.
* **Survey drone (P4 and E4).** ASSUMPTION: P(survey reports a bloom | clear) 0.05, | developing
  0.6, | at intake 0.9, independent of whether the satellite can see the bloom; weather
  availability 0.8 by default; result available within 4 hours, applied to the same day's
  decision; cost 1,000 CU per sortie by default.
* **Metrics per run** (never collapsed): unserved water (m3), forced shutdowns, cleaning
  events (forced plus planned), membrane life consumed (index), PARK days, DERATE days,
  escalation days, advisory changes per 30 days, survey sorties, and regret versus the oracle.
* **Weighted cost** (secondary view, hypothetical cost units CU): forced shutdown 40,000;
  any cleaning 10,000; unserved water 10 per m3; membrane life 5,000 per index unit; a derated
  day 500 (coagulant); a restart 2,000; a sortie its cost. Regret = policy cost minus oracle
  cost on the same seed. A weight sensitivity run halves and doubles each weight in turn.
* **Statistics.** Means over seeds with 95 percent intervals (mean plus or minus 1.96 standard
  errors; for regret differences the interval of the paired difference).

## Policies

* P0 always_go: q = 1 every day.
* P1 alert_park: PARK for 7 days after any alert, otherwise GO.
* P2 seasonal_rule: DERATE at q = 0.7 with the coagulant boost from 15 August to 31 October and
  from 15 January to 15 March, otherwise GO.
* P3 madkhal_no_inspect: the estimator and decision engine.
* P4 madkhal_inspect: P3 plus a sortie whenever the value of information times availability
  exceeds the sortie cost; a flown survey updates the belief before the decision.
* P5 oracle: knows the true bloom states, bloom load and truth plant; each day it picks the
  candidate with the lowest weighted cost over the next 72 hours by simulation. An upper bound
  on achievable performance (it is myopic beyond 72 hours, so it is not a proven optimum).

## Generators

* **G1 (calibrated).** The estimator's own model with parameters at their posterior means:
  false alarm rate, hit rate, blind spot share, alert rates, onset rate and transition rates;
  Kalba's real monthly clear shares; Pareto bloom load from the truth plant.
* **G2 (stress, structurally different).** Starts from G1 and changes structure: bloom load
  tail index multiplied by 0.6 (heavier tail); detector misses correlated within a bloom (after
  a miss on a clear day, the next clear day misses with probability 0.8); clear sky share from
  June to September multiplied by 0.4 (longer blind season); an extra stream of species events
  invisible to the satellite at 0.5 per year; false alarms clustered into episodes (start with
  probability alpha / 3 on a clear quiet day, then an alert on each following clear day with
  probability 0.7), keeping the marginal false alarm rate near alpha.

## Experiments and predictions

### E1 Estimator quality (G1, 30 seeds)

Question: does the filter forecast P(bloom at the intake within 3 days) better than the
baselines alert_means_bloom and persistence (alert state held 7 days)?
Metrics: Brier score, log score (probabilities clipped to 0.01 and 0.99), reliability by
forecast decile, and coverage of the 90 percent interval: the share of days on which the
interval over draws contains the probability computed by the same filter with the true G1
parameters.

* PR-E1-1: the filter's mean Brier score is lower than both baselines, and at most 0.6 times
  the persistence baseline's.
* PR-E1-2: the filter's mean log score is lower than both baselines.
* PR-E1-3: the 90 percent interval coverage is at least 0.85.
* PR-E1-4: in reliability bins holding at least 50 days, the observed frequency is within 0.1
  of the mean forecast in at least 80 percent of bins.

### E2 Policy comparison (G1, 30 seeds)

* PR-E2-1: P3 has at most half the forced shutdowns of P0 (mean).
* PR-E2-2: P1 has more than 10 times the unserved water of P3 (mean).
* PR-E2-3: P3's mean regret is lower than that of P0, P1 and P2.
* PR-E2-4: P3 has between 5 and 40 DERATE days per year (mean).
* PR-E2-5: the oracle's mean weighted cost is the lowest of all policies.

### E3 Robustness (G2, 30 seeds)

* PR-E3-1: every policy except the oracle has a higher mean regret on G2 than on G1.
* PR-E3-2: P3's mean regret on G2 is at least 1.5 times its regret on G1.
* PR-E3-3: on G2, P3's mean regret is higher than P2's (the simple seasonal rule beats
  Madkhal when the detector model is wrong).

### E4 Value of inspection (G1, 20 seeds, stated reduction)

Grid: weather availability 0.2, 0.6, 1.0 and sortie cost 250, 1,000, 4,000, 16,000 CU.

* PR-E4-1: at availability 1.0 and cost 1,000 CU, P4's mean weighted cost is below P3's.
* PR-E4-2: the break even sortie cost at availability 1.0 lies between 1,000 and 20,000 CU.
* PR-E4-3: at availability 0.2 and cost 16,000 CU, INSPECT does not pay: P4's mean cost is not
  below P3's.
* PR-E4-4: at availability 1.0 and cost 1,000 CU, P4 flies between 2 and 60 sorties per year.

### E5 Sensitivity (G1, 10 seeds, stated reduction)

Truth parameters (plant physics, and the detector's false alarm rate, visible share and alert
rate) are moved one at a time by plus and minus one spread, and in a random design of 40 truth
samples; influence on P3's regret is measured by the swing and by Spearman rank correlation.

* PR-E5-1: at least one detector parameter is among the three most influential by absolute
  rank correlation.
* PR-E5-2: the plant parameter with the largest swing is one of the pretreatment capacity,
  the bloom load lower bound or the tail index.

### E6 Stability (from the E2 runs)

* PR-E6-1: P3 and P4 change advice at most 2 times per 30 days on average.
* PR-E6-2: dwell compliance is 100 percent. Stated in advance: with daily decisions the 12 hour
  dwell cannot bind, so this is a check of the implementation, not of a design choice.

### E7 Replay on real evidence (no performance claim)

Kalba, Barka and Al Raha, 2018 to 2023, real OLCI coverage and alerts, hypothetical plant in a
neutral state, 400 draws. Reported: non GO advisory days per year on Nadhir's held out quiet
days and on all days outside event windows, and the advisory and belief 14, 7 and 3 days
before each documented t_ref and t_ref_earliest.

* PR-E7-1: on Nadhir's held out quiet days, non GO advisory days per year are at most 15 at
  every site.
* PR-E7-2: 3 days before the Kalba 2018 t_ref the advisory is not GO (not blind, see above).
* PR-E7-3: 3 days before the Barka 2018 and Barka 2023 t_ref the advisory is GO (the detector
  missed both).
* PR-E7-4: at every point before the Al Raha 2023 dates the advisory is GO (species blind spot).

## Amendments

None yet.
