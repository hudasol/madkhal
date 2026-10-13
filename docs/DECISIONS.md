# Decisions log

Readings of the build brief where it was silent or ambiguous, and the reason for each.
Larger architectural decisions have their own ADR in `docs/adr/`.

| ID | Decision | Reason |
|---|---|---|
| D-001 | Requirements carry a `phase` field, and the fast check enforces "every MUST requirement has a test" only for phases already reached (`enforced_through` in `docs/requirements.yaml`). At v1.0.0 every phase is enforced. | The brief asks for `madkhal check` to pass on every commit and also for every MUST requirement to have a test. Both hold only if requirements of later phases are not enforced before they are built. The matrix marks them "not yet built" rather than hiding them. |
| D-002 | Web tests name requirement IDs inside their test titles (for example `it("MK-L8-002 banner ...")`); Python tests use `@pytest.mark.req("MK-...")`. One scanner reads both. | Keeps one traceability matrix across the Python and TypeScript halves. |
| D-003 | A claim of kind `url` resolves only if the page is listed in `docs/sources_opened.yaml` with the date it was opened. | Tests cannot fetch pages (no runtime network calls), so the register records which pages were actually opened during the build. |
| D-004 | "Observable" means at least 5 clear satellite days in the 121 day lookback at 50 km. | Reproduces Nadhir's own classification (3 observable, 2 not); any threshold from 2 to 20 gives the same split (ADR 0002). |
| D-005 | Events are shown with neutral labels written in the adapter (place, year, kind), never with Nadhir's `name` or `plants` fields, which name operators. The snapshot keeps Nadhir's text verbatim because it is hash checked data. The operator name scan excludes `data/nadhir_snapshot/`. | The brief says to name no operator in the UI or code, and also that places and documented events may appear as they do in Nadhir. Showing the place, date and evidence status satisfies both. |
| D-006 | Each event carries a short `status_badge` that must contain "UNVERIFIED" whenever any part of the verbatim status is unverified (enforced by the contract). The Fujairah 2008 to 2009 event shows "VERIFIED-SECONDARY, dates UNVERIFIED". | Its Nadhir status is verified for plant losses but unverified for dates; a coarse class alone would hide the unverified part. |
| D-007 | Snapshot bytes come from git blobs at the pinned commit, not from the reference clone's working tree. | The clone was checked out with CRLF conversion; blob bytes are platform independent and match the hash Nadhir itself recorded for `events.yaml`. |
