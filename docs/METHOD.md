# Method

Madkhal answers one question for a hypothetical seawater reverse osmosis (SWRO) intake: given
satellite bloom evidence that is sometimes blind and sometimes wrong, what should the operator
do with the intake today, how sure are we, and when is it worth sending a drone to look?

Evidence: real satellite history from the Nadhir hindcast. Plant, drone and consequences:
hypothetical, synthetic parameters. Madkhal is advisory software for planning and learning; it
controls nothing and has no connection to any plant system.

## 1. Evidence (real)

The Nadhir hindcast scored a frozen chlorophyll anomaly detector on Sentinel 3 OLCI (300 m,
2018 to 2023) and MODIS Aqua (4 km, 2003 to 2014) before looking at any event. Madkhal reads a
pinned, hash checked copy of its outputs (ADR 0002): one state per site and day (no usable
view, quiet, exceedance, alert), held out false alarm counts, and the outcome for each dated
event. Of five dated disruptions, the detector caught one (Kalba 2018), missed two (Barka 2018
and 2023) and could not observe two (RAK and Dibba 2008, in the MODIS summer blind spot). A
documented diatom bloom at Al Raha in April 2023 produced no broadband anomaly at all: the
species level blind spot.

## 2. Belief (estimator)

A Bayesian filter tracks three states: clear, developing in the 50 km watch zone, and at the
intake (ADR 0003). Internally each bloom state is split into visible and invisible to the
broadband detector. A new bloom is visible with probability hit rate times (1 minus blind
spot share), so quiet days can rule out visible blooms but never invisible ones.

* Days without a usable view carry no information: the belief is propagated, not updated
  (ADR 0004).
* The false alarm rate, the hit rate and the in bloom alert rate are uncertain and carried as
  posterior distributions from Nadhir's counts, deliberately wide because the samples are tiny
  (ADR 0005). Transition rates and their seasonal shape are assumptions.
* The filter runs over 400 posterior draws at once and reports, per day, P(bloom at the intake
  within 1, 3 and 7 days) and P(any bloom) as medians with 90 percent intervals, and the days
  since the last clear view.

## 3. Plant (hypothetical)

A stylised SWRO unit: offshore intake, coagulation with dissolved air flotation, one RO train
and a product water store (`docs/PARAMETERS.md`). The bloom adds a heavy tailed (Pareto) load
at the intake; load above pretreatment capacity breaks through and raises a fouling index; at
the hard limit (fouling index 1) the plant trips into a forced cleaning with a restart penalty.
PARK is not free: production stops and storage drains, and unserved water accrues when storage
is empty. Every plant parameter is an assumption at evidence level L0.

## 4. Decision

For each candidate action (GO, DERATE at 0.9 to 0.2 with a coagulant boost, PARK) the engine
simulates the plant over 72 hours for every posterior draw and every possible current state,
and computes two probabilities: reaching the fouling limit, and unserved water beyond the
allowance. The most permissive action that keeps both within 5 percent is advised; if none
does, the advice is NO SAFE OPTION, ESCALATE, with the least bad option named (ADR 0007). The
construction guarantees that worse evidence (a higher bloom probability, wider plant spreads,
a tighter budget, lower storage) never yields a more permissive advice; property tests check
each case. A 12 hour dwell and a hysteresis margin keep the advice from flapping (ADR 0008).
Each advisory carries a structured explanation (inputs, every candidate's risks, the binding
constraint, evidence level, assumption share) from which three sentences are rendered: what to
do, why, and what would change it. Its id is the SHA-256 of its inputs, so it can be
reproduced from stored inputs and a seed.

## 5. Inspection (drone)

INSPECT is advised only when a survey pays for itself: its pre posterior value of information,
times the weather availability, exceeds the sortie cost (ADR 0010). Survey missions are
generated for simulation and review only.

## 6. Evaluation

Seven experiments were preregistered before any result existed (`docs/PREREGISTRATION.md`):
estimator quality, policy comparison, robustness on a structurally different world, value of
inspection, sensitivity, stability, and a replay over the real 2018 to 2023 evidence. Results
and every prediction marked as a hit or a miss are in `docs/EVALUATION.md`, rendered from
`results/*.json`.

## 7. Language

The Arabic interface copy and the Arabic field descriptions are machine drafted. A native
speaker should review them before any use with Arabic speaking readers.
