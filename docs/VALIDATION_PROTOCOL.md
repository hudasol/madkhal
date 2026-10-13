# Validation protocol (proposal)

How Madkhal should be validated before anyone relies on it. None of these steps has been done
with real plant data; today the evidence level of the plant model is L0 and the decision layer
is validated only against synthetic worlds (`docs/EVALUATION.md`).

## Levels (from Dhill)

| Level | Meaning | What it takes |
|---|---|---|
| L0 | uncalibrated, assumptions and illustrative values | the current state |
| L1 | parameterised from datasheets or the literature | each value cited to a source that was opened |
| L2 | calibrated on the operator's field data | the data in `docs/PILOT.md`, a calibration split, and the frozen model below |
| L3 | independently validated | a second party repeats the held out scoring without the author |

## Steps for L2

1. **Split before looking.** Choose calibration years and held out years before opening the
   operator's data, as Nadhir did for its detector (blind protocol). Write the split down and
   commit it.
2. **Calibrate** plant parameters on the calibration years only. Record each fitted value,
   its uncertainty and the data rows used. Freeze the profile with a hash.
3. **Preregister** predictions for the held out years, in the style of
   `docs/PREREGISTRATION.md`: forced shutdowns per year, fouling index trajectories during
   documented blooms, advisory days per year, and the advisory state before each recorded
   disruption.
4. **Score** on held out years: Brier and log scores for the bloom belief against operator
   bloom records; calibration of the 90 percent intervals; for the decision, the share of
   recorded forced shutdowns preceded by DERATE, PARK or ESCALATE, and the advisory burden on
   quiet days. Report hits and misses.
5. **Shadow mode.** Run read only beside operations for at least one bloom season. The advice
   is logged, not acted on, and reviewed with operators after the season.
6. **Decide** with the operator whether the tool is useful, and what to change. A negative
   result is reported as such.

## What would invalidate the approach

* The fouling index does not follow breakthrough in the recorded pressure series.
* Satellite alerts carry no information about intake conditions in the operator's records
  (the posterior hit rate stays near the false alarm rate).
* Operators find the advisory burden on quiet days too high to be useful.
