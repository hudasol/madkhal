# Limitations

Read this before drawing any conclusion from Madkhal.

## About the evidence

* **One detection.** The detector's hit rate rests on one detected event among three
  observable dated disruptions. The posterior is deliberately wide; any statement about
  detection skill is weak.
* **Dates are upper bounds.** Most event dates are UNVERIFIED news report dates, not operator
  logs. Lead times measured against them are optimistic by up to the gap to the earliest
  consistent date. This is the largest single uncertainty.
* **Coordinates are estimated.** Intake positions are town or plant positions, not surveyed
  intakes.
* **Species level blind spot.** A documented diatom bloom produced no broadband anomaly. The
  model keeps invisible blooms possible, but nothing can detect them from this evidence.
* **Clustered false alarms.** Alert days are treated as conditionally independent given the
  state, although they come in episodes. A long false alarm episode raises the belief strongly.
* **Summer blindness of MODIS.** The MODIS archive has no usable summer days on the east coast,
  so the older dated events cannot be scored at all.

## About the model

* **Hypothetical plant.** Every plant parameter is an assumption (evidence level L0). The plant
  resembles no real asset; its fouling physics is a stylised index, not a membrane model.
* **Conservative by construction.** The decision samples uncertain physics towards its adverse
  side (ADR 0007). This guarantees that worse evidence never relaxes the advice, at the price of
  extra derating while the plant is uncalibrated.
* **Constant action over the horizon.** Each candidate is evaluated as if held for 72 hours.
  This makes PARK look worse than a short park followed by a restart would.
* **Daily decisions in the lab.** With daily decisions the 12 hour dwell cannot bind; only the
  hysteresis margin limits flapping there.
* **English explanations.** The three plain language sentences of an advisory are produced in
  English; the interface localises everything else and marks those sentences as English.
* **Two monotonicity properties hold only in their stated form.** A nodata day never moves the
  belief away from the seasonal prior, but it can narrow the interval; an extra alert raises
  P(any bloom) on its own day but, followed by quiet days, can lower it later (D-008, D-009).
* **Alarm discipline gives way to water security.** When the action in force and every more
  restrictive option breach a budget, the dwell and hysteresis rules give way and the advice
  relaxes to the smallest option within budget. In that one case a worse belief can give a
  less restrictive action than before (ADR 0008, amendment). The independent review found the
  earlier rule reporting NO SAFE OPTION when a safe option existed.

## About the evaluation

* **Synthetic worlds by the same author.** G1 shares the estimator's assumptions and flatters
  it. G2 breaks five assumptions but is still written by the method's author.
* **Small advantages are not established.** On G1, Madkhal's mean regret is lowest among the
  practical policies, but its paired intervals against always going and against the seasonal
  rule include zero. On G2 the seasonal rule's mean regret is lower than Madkhal's.
* **Normal intervals on skewed counts** can extend below zero.
* **The replay makes no performance claim.** It shows the advice that would have been displayed
  on real evidence, against a plant in a neutral state.
* **Nothing is validated against a real plant or operator logs.**

## About the software

* **Performance margin is thin for the experiment suite.** The full suite ran in 833 s against
  a 900 s budget on one machine, and in 871 s on an earlier run (`results/performance.json`,
  `results/run.json`); a slower machine will exceed it. The other four measures have wide
  margins. One attempted run on a loaded machine lost a worker process and wrote nothing.
* **Accessibility is checked automatically only.** axe passes on every screen in both languages
  and themes, but no manual screen reader pass was done (K-006).
* **Arabic is machine drafted and partial.** The interface is translated, but the advisory
  sentences and the method documents are shown in English (K-001, K-002, K-008).

## Engineering lens: self score

Scored hard, one line each, with the evidence.

| Criterion | Score | Evidence |
|---|---|---|
| Reliability and safety first | Partly met | Advice never becomes more permissive when the bloom probability rises, spreads widen, budgets tighten or storage falls while the alarm discipline rules hold (hypothesis property tests, `tests/test_decision.py`; the one exception is stated in ADR 0008); but the advice cannot react to blooms the satellite cannot see, which are most blooms in G1, and Madkhal cut forced shutdowns by less than half against always going (PR-E2-1 missed). |
| Operator in the loop | Met | No control actions, no writes to any system, read only API; the scope statement is on every screen footer and in every export. |
| Alarm discipline | Partly met | Dwell, hysteresis and a measured change rate (E6); at the daily cadence of the lab the dwell rule is not exercised, so its value is shown only in hourly use, and the dwell compliance hit is vacuous (D-015). The independent review found the original dwell rule hiding a safe option; it was fixed (D-012). |
| Water security | Met in the model | Unserved water risk is a constraint beside fouling risk and NO SAFE OPTION, ESCALATE is shown exactly when every option breaches (property test over every action in force, dwell time and storage level; MK-L4-004, MK-L4-009); untested against real storage practice. |
| Auditability | Met | Every advisory carries its inputs hash and seed, reproduces exactly from stored inputs (MK-L4-011) and explains itself from a structured object; results reproduce byte for byte across runs. |
| Honest uncertainty | Partly met | Intervals everywhere and small samples shown with counts; but the 90 percent intervals were wider than needed on G1 (coverage of one) and calibration on worlds far from the posterior mean is unmeasured. |
| Maintainability | Met | Nine layers with enforced import contracts, strict typing, generated contract artefacts, a requirement matrix with a test per MUST, ADRs for each real decision. |

## What would close the main gaps

Operator logs with timestamps (`docs/PILOT.md`), more detected events, a hyperspectral or
species aware signal for the blind spot, and a validation run that follows
`docs/VALIDATION_PROTOCOL.md`.
