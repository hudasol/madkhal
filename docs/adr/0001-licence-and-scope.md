# ADR 0001: Licence, scope and attribution

**Status:** accepted (P0).

## Context

Madkhal is a proposal seed prepared by a student. It turns real satellite bloom evidence
from the Nadhir hindcast into advisories for a hypothetical seawater reverse osmosis (SWRO)
intake. It reuses ideas from two earlier projects by the same author: Nadhir (the evidence
source) and Dhill (decision semantics). Dhill has no licence selected.

## Decision

1. Madkhal is released under the Apache License 2.0 (`LICENSE`, the unmodified text from
   apache.org). Apache 2.0 is permissive, carries an explicit patent grant and is common in
   public sector and utility open source work.
2. Madkhal is advisory software for planning and learning. It has no connection to any
   plant system, issues no control actions and writes to no external system. Any future
   integration would be read only. This scope statement is repeated in the README, the
   Method screen and every exported mission.
3. Nadhir is used as data, not as a dependency: a pinned snapshot of its output files is
   copied into `data/nadhir_snapshot/` with a manifest (see ADR 0002).
4. Dhill ideas are ported, not imported. Because both projects are the author's own work,
   porting ideas or small pieces is allowed although Dhill has no licence. Each ported piece
   is listed below with its source file and commit, and the README credits Dhill.

## Ported from Dhill (commit b751f002a6c61a599940c7ee932e533fbcfec627)

| Madkhal piece | Dhill source | What was ported |
|---|---|---|
| Action semantics GO, DERATE, PARK with binding constraint, P(exceed hard limit), time to limit | `src/dhill/envelope.py`, `src/dhill/models.py` | Idea and field names; re implemented for a fouling and water security problem |
| Evidence levels L0 to L3 and assumption share | `src/dhill/profiles/schema.py` | Level definitions and the assumption fraction idea |
| Spread follows provenance | `docs/adr/0003-uncertainty-by-provenance.md` | The rule that assumptions get large spreads and measurements small ones |
| One at a time sensitivity ranking ("measure this first") | `src/dhill/sensitivity.py` | Method idea (swing per prior standard deviation, ranked) |
| Policy comparison on a hidden truth model | `src/dhill/policies.py` | The idea of scoring the engine against simple operator rules and reporting where the rule is competitive |

No Dhill code is imported at runtime. Madkhal has no runtime dependency on Dhill or Nadhir.

## Consequences

The licence is recorded once here and in `pyproject.toml`. Any further ported piece must be
added to the table above in the same commit that ports it.
