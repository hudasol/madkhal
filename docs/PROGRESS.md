# Progress

Updated at every phase gate. Phases follow the build plan (P0 to P10).

## Preflight (2026-10-13)

| Check | Result |
|---|---|
| Python | `py -3.13 --version`: Python 3.13.0 (used for `.venv`). `python --version`: not on PATH (Windows store alias only). |
| Node | v24.15.0 |
| npm | 11.12.1 |
| git user.name | set |
| git user.email | set |
| Free disk space | 124 GB free on the working drive |
| pip registry | reachable (`pip index versions pydantic` answered) |
| npm registry | reachable (`npm view react version` answered) |
| Playwright Chromium | installed (`npx playwright install chromium`, exit 0) |

Reference clones are present at the pinned commits: Nadhir `ca484e2`, Dhill `b751f00`.

## Phase status

| Phase | Status | Tag | Evidence |
|---|---|---|---|
| P0 skeleton, tooling, harness | done | v0.1.0 | `madkhal check` passes on the skeleton (lint, mypy strict, import contracts, traceability, claims, 13 unit tests) |
| P1 contract | done | v0.2.0 | 27 contract models; JSON Schema, TypeScript types and bilingual field dictionary generated; `test_generated_artefacts_are_fresh` passes |
| P2 evidence | done | v0.3.0 | Snapshot of 41 files hash checked; corruption tests name file, row and column; all 8 event statuses kept verbatim; track record 5 dated, 3 observable, 1 detected; quiet day rule reproduces Nadhir's counts for 7 sites |
| P3 estimator | done | v0.4.0 | Worked example by hand matches the filter; property tests for nodata (exact propagation, total variation contraction) and alerts (same day) pass; E1 smoke runs from `madkhal eval --smoke`; replay is causal and deterministic. Note: at intermediate commit `77db054` the fast check would fail its freshness step because `docs/TRACEABILITY.md` was committed one commit later (`cb7c766`); the matrix is now committed together with its tests. |
| P4 walking skeleton | done | v0.5.0 | API tests pass (19); web unit tests pass (11); the same 5 Playwright checks pass against the static build (no backend) and against the live build with `madkhal serve`, with no request outside the app's own origin; screenshots of Console, Evidence and Arabic Console were reviewed and four layout defects fixed (legend sizing, right to left chart labels, untranslated "to", raw site ids) |
| P5 plant and decision | done | v0.6.0 | 25 plant and decision tests pass, including hypothesis property tests for all four safety monotonicity properties, dwell, reproducibility from stored inputs, and water and load balance; advisory, timeline, scenario and plant endpoints tested |
| P6 policy lab | done | v0.7.0 | `docs/PREREGISTRATION.md` committed (`b831025`) before any results file; generators G1 and G2, policies P0 to P5 and the experiment runner exist; the oracle sanity test passes on development seeds; 16 lab tests pass (value of information never negative, perfect free sensor inspects exactly when the action could change) |
| P7 evaluation | done | v0.8.0 | `madkhal eval` wrote `results/e1.json` to `e7.json` on 30 evaluation seeds (E4 20, E5 10, as preregistered); `docs/EVALUATION.md` is rendered from them and a test fails on any difference; 21 of 24 predictions hit, 3 misses kept and explained. The first run took 1,122 s; after making the risk table memo persistent per worker, a second run produced byte identical results in 871 s, inside the 15 minute budget |
| P8 tasking | done | v0.9.0 | Survey missions with refusal over endurance, wind availability, GeoJSON, KML and a QGroundControl plan that passes the validator, all with the simulation only notice; value of information never negative (property test); missions endpoint tested; E4 in the results |
| P9 full console | done | v0.10.0 | Ten screens in English and Arabic, light and dark; 44 web unit tests pass (contrast in both themes, shape and pattern encodings, chart labels with table alternatives, loading and error states, Asia/Dubai times); 47 Playwright tests pass against the static build, including axe on 10 screens in 4 language and theme combinations with no request outside the app's own origin; 120 design QA screenshots (1440, 1024 and 768 px) were captured and reviewed, and the defects found were fixed (oversized glyphs, rounding of small values, dwell bar colour, untranslated lab states and units). Gaps recorded as K-001, K-002, K-006 and K-008 |
| P10 hardening | done | v1.0.0 | Performance budget measured and met for all five measures (`results/performance.json`); dependency audits clean after upgrading three web packages; an independent reviewer, given only the repository and the mission, constraints and definition of done, reported ten findings: eight fixed (among them a dwell rule that could show NO SAFE OPTION when a safe option existed, and a flaky property test), one rejected and one recorded as a qualification (D-012 to D-015); the experiments were run again after the decision fix (only two G2 escalation figures changed, no prediction changed); 120 design QA screenshots captured again and reviewed; `madkhal check`, the slow tests, 45 web unit tests and 48 Playwright tests pass; coverage 86 percent; `madkhal all --skip-eval` passed from a fresh clone in a new virtual environment and left every tracked file unchanged apart from the two timing files (a clone in a very long folder hit the Windows path limit, K-009). Process slip: two P10 commits use the type `results`, which is not in the agreed list; history is not rewritten |

## Blockers

None.
