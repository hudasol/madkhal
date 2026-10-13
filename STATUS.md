# Status

What works today, in plain words.

Evidence: real satellite history from the Nadhir hindcast. Plant, drone and consequences:
hypothetical, synthetic parameters. Madkhal is advisory software for planning and learning;
it controls nothing.

## Works

- **Evidence.** A pinned, hash checked snapshot of the Nadhir hindcast outputs is read by one
  adapter that fails loudly on any altered or unexpected file. It gives the daily coverage
  calendar and the detector track record (5 dated events, 3 observable, 1 detected), with every
  event's evidence status kept verbatim.
- **Belief.** A Bayesian filter runs over the real daily evidence with 400 parameter draws and
  reports P(bloom at the intake within 1, 3 and 7 days) with 90 percent intervals. Days without
  a satellite view carry no information.
- **Advice.** A hypothetical SWRO plant model and a decision engine give GO, DERATE, PARK or NO
  SAFE OPTION, ESCALATE with reasons, the binding constraint, P(fouling breach), time to limit,
  evidence level and assumption share, and an INSPECT advisory when a drone survey would pay for
  itself. Worse evidence never relaxes the advice while the alarm discipline rules hold, and
  NO SAFE OPTION is shown exactly when every option breaches a budget (property tests; ADR 0008
  states the one exception).
- **Evaluation.** Seven preregistered experiments run with `madkhal eval`; 21 of 24 predictions
  hit and the 3 misses are kept and explained (`docs/EVALUATION.md`).
- **Missions.** Survey missions around the estimated intake export to GeoJSON, KML and a
  QGroundControl plan that passes a structural validator, each with the simulation only notice
  and the advisory scope statement (`madkhal plan`).
- **API.** `madkhal serve` serves everything under `/v1` with problem+json errors;
  `madkhal static` builds a static demo that needs no backend.
- **Console.** Ten screens (Console, Timeline, Evidence, Scenario Lab, Policy comparison,
  Inspection, Plant model, Replay, Method and limits, Shift handover) in English and Arabic,
  light and dark, with the two part banner on every screen. Automated accessibility checks
  (axe) pass on every screen in both languages and both themes.
- **Hardening.** The performance budget is measured and met (`results/performance.json`);
  `pip-audit` and `npm audit` report no known vulnerabilities (`results/*_audit.txt`); an
  independent review was run and its findings fixed or answered (`docs/DECISIONS.md`, D-012 to
  D-015).

## Known gaps

See `docs/KNOWN_ISSUES.md` and `docs/LIMITATIONS.md`. In short: the plant is hypothetical and
uncalibrated, the detector's hit rate rests on one detected event, the plain language advice
sentences are English only, and the Arabic copy is machine drafted.
