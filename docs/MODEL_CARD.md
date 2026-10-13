# Model card

## Purpose

Advisory decision support for a hypothetical seawater reverse osmosis intake under satellite
algal bloom evidence. It answers: what to do with the intake today (GO, DERATE, PARK or NO SAFE
OPTION, ESCALATE), how sure the evidence is, and whether a drone survey would pay for itself.
For planning and learning only. It controls nothing.

## Components

| Component | What it is | Evidence level |
|---|---|---|
| Bloom estimator | Bayesian filter over clear, developing and at_intake states with a visibility latent, run over 400 posterior parameter draws (ADR 0003 to 0005) | Detector rates from Nadhir counts (one detected event, three observable); transitions are assumptions |
| Plant model | Stylised SWRO unit: Pareto bloom load, breakthrough driven fouling with a hard limit, storage and unserved water | L0: every parameter an assumption |
| Decision engine | Chance constrained choice over 10 candidate actions, monotone in bad news by construction, with dwell and hysteresis (ADR 0007, 0008) | Inherits the plant's L0 |
| Inspection value | Pre posterior value of a survey against its cost (ADR 0010) | Survey sensor is an assumption |

## Intended use

Exploring how imperfect satellite evidence could feed intake decisions; teaching; discussing a
pilot with an operator. Not for operating a plant.

## Out of scope

Real time operations, control, any decision affecting supply or safety, any claim about a real
plant's past or future behaviour, flight planning.

## Data

Real: Nadhir hindcast outputs (Sentinel 3 OLCI 2018 to 2023, MODIS Aqua 2003 to 2014), with
evidence statuses kept verbatim (`docs/DATA_STATEMENT.md`). Synthetic: everything about the
plant, the drone, the policy lab worlds and the costs.

## Evaluation

Seven preregistered experiments; results, hits and misses in `docs/EVALUATION.md`, rendered
from `results/*.json`. Synthetic worlds flatter the method (G1 shares its assumptions); the
stress world G2 is reported beside it. The replay on real evidence makes no performance claim.

## Known limitations

See `docs/LIMITATIONS.md`. The most important: the hit rate rests on one detected event; most
blooms in the synthetic worlds are invisible to the broadband detector, so the advice cannot
react to them; the plant is hypothetical; event dates are mostly upper bounds.

## Ethics and safety

No personal data. No operator is named outside `docs/CONTEXT.md`. Uncertainty is shown
everywhere; the advice is more conservative when evidence or calibration is weaker.
