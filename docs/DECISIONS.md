# Decisions log

Readings of the build brief where it was silent or ambiguous, and the reason for each.
Larger architectural decisions have their own ADR in `docs/adr/`.

| ID | Decision | Reason |
|---|---|---|
| D-001 | Requirements carry a `phase` field, and the fast check enforces "every MUST requirement has a test" only for phases already reached (`enforced_through` in `docs/requirements.yaml`). At v1.0.0 every phase is enforced. | The brief asks for `madkhal check` to pass on every commit and also for every MUST requirement to have a test. Both hold only if requirements of later phases are not enforced before they are built. The matrix marks them "not yet built" rather than hiding them. |
| D-002 | Web tests name requirement IDs inside their test titles (for example `it("MK-L8-002 banner ...")`); Python tests use `@pytest.mark.req("MK-...")`. One scanner reads both. | Keeps one traceability matrix across the Python and TypeScript halves. |
| D-003 | A claim of kind `url` resolves only if the page is listed in `docs/sources_opened.yaml` with the date it was opened. | Tests cannot fetch pages (no runtime network calls), so the register records which pages were actually opened during the build. |
