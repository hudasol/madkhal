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
| P6 policy lab | in progress | | |
| P7 evaluation | | | |
| P8 tasking | | | |
| P9 full console | | | |
| P10 hardening | | | |

## Blockers

None.
