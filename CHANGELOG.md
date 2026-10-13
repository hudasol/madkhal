# Changelog

All notable changes, by phase tag.

## v1.0.0 (P10)

- Performance budget measured by `madkhal perf` and a Playwright test, recorded in
  `results/performance.json` and `results/performance_web.json`; all five measures are within
  budget.
- `madkhal audit` (pip-audit on the lock file), `madkhal plan` (mission exports) and
  `madkhal lab` (Scenario Lab presets); `madkhal all` now also measures performance, audits
  dependencies and writes the SBOM.
- Test that no operator name, logo file or affiliation appears outside `docs/CONTEXT.md`.
- ADR 0011 (map without tiles) and ADR 0012 (determinism).
- Independent review fixes: dwell and hysteresis now give way to the smallest relaxation
  within budget when the action in force breaches, so NO SAFE OPTION is shown exactly when
  every option breaches (ADR 0008 amendment, new property tests); a flaky plant property test
  restated on the capped index; mission exports carry the advisory scope statement; source
  URLs that name an organisation moved out of the claims register; the Console chart shows an
  error state instead of loading forever; copy fixes. Rejected and qualified findings are in
  `docs/DECISIONS.md` (D-012 to D-015).
- Web dependencies upgraded after an audit (`maplibre-gl` 6, `react-router-dom` 7, `vitest` 5);
  the end to end tests now also fail on any console error.
- `madkhal check` and CI run Hypothesis derandomized, so the gate gives the same answer on
  every run.

## v0.10.0 (P9)

- Full console: Timeline, Scenario Lab, Policy comparison, Inspection, Plant model, Replay,
  Method and limits, and Shift handover, in English and Arabic, light and dark.
- Action encodings by shape and pattern as well as colour; every chart has a label, intervals
  and a table alternative; axe checks on every screen in four language and theme combinations.
- Schematic inspection map from a local Natural Earth coastline; no tile service.
- `madkhal static` builds the static demo in one command; `madkhal all` runs everything.
- README, MODEL_CARD, SECURITY, DATA_STATEMENT and LIMITATIONS written.

## v0.9.0 (P8)

- Survey missions with refusal over endurance, hypothetical wind availability and value of a
  survey; exports to GeoJSON, KML and a QGroundControl plan with a structural validator, each
  with the simulation only notice. Missions endpoint.

## v0.8.0 (P7)

- `madkhal eval` runs the preregistered experiments E1 to E7 and writes `results/*.json`;
  `docs/EVALUATION.md` is rendered from them with every prediction marked as a hit or a miss.

## v0.7.0 (P6)

- `docs/PREREGISTRATION.md` committed before any result. Policy lab with the calibrated (G1)
  and stress (G2) generators and policies P0 to P5.

## v0.6.0 (P5)

- Hypothetical SWRO plant model and the decision engine (GO, DERATE, PARK, NO SAFE OPTION,
  ESCALATE) with property tests for the safety monotonicity rules, dwell and reproducibility.
  Advisory, timeline, scenario and plant endpoints.

## v0.5.0 (P4)

- Walking skeleton: versioned API with problem+json errors, static snapshot, and the Console
  and Evidence screens in live and static modes.

## v0.4.0 (P3)

- Bayesian bloom state filter that treats days without a satellite view as missing
  information, with parameter posteriors from Nadhir's counts, baselines and a replay command.

## v0.3.0 (P2)

- Pinned, hash checked snapshot of the Nadhir hindcast outputs; adapter with loud failures,
  coverage calendar and detector track record with every event status kept verbatim.

## v0.2.0 (P1)

- Contract models with generated JSON Schema, TypeScript types and a bilingual field
  dictionary, and a freshness test.

## v0.1.0 (P0)

- Repository skeleton with nine layer packages and the `madkhal` command line tool.
- Fast check: ruff, mypy strict, import-linter layer contracts, traceability, claims, unit tests.
- Requirements file with tiers and phases; traceability matrix and claims register rendered.
- ADR 0001: Apache 2.0 licence, advisory scope and attribution of ported ideas.
