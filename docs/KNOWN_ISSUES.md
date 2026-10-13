# Known issues

Documented gaps. Each entry says what is missing, why, and what would close it.

| ID | Issue | Why | What would close it |
|---|---|---|---|
| K-001 | The three plain language sentences of an advisory (what, why, what would change it) and the reasons are produced in English only. The Arabic interface shows them marked as English (`lang="en"`, `dir="ltr"`). | The sentences are rendered on the server from the explanation object; a second renderer per language was not built. | Render the sentences in the web app from the structured explanation with the i18n catalogue. |
| K-002 | The Arabic copy is machine drafted. | No native speaker review was available during the build. | Review by a native speaker. |
| K-003 | In the static demo the advisory is precomputed for the last evidence day only; the Scenario Lab offers four presets instead of free scenarios; the Inspection screen shows the default mission. | A static host cannot compute. The screens say so. | Use the live API (`madkhal serve`). |
| K-004 | The QGroundControl plan has been validated against its documented structure only; it has not been loaded in QGroundControl. | No ground station was run in this project. | Load the exported plan in QGroundControl and record the result. |
| K-005 | The decision layer's dwell rule is not exercised by the daily lab simulation (decisions are 24 hours apart). | Evidence arrives daily. | An hourly lab cadence, at higher cost. |
| K-006 | The axe checks cover WCAG 2 A and AA rules that can be tested automatically; manual checks with a screen reader were not done. | Time. | A manual screen reader pass in both languages. |
| K-007 | One intermediate commit (`77db054`) would fail the freshness step of the fast check because `docs/TRACEABILITY.md` was committed one commit later. | Process slip, recorded in `docs/PROGRESS.md`; history is not rewritten. | None needed; later commits keep the matrix with its tests. |
| K-008 | The Method and limits screen shows the method, limitations and pilot documents in English in the Arabic interface (marked `lang="en"`, `dir="ltr"`). | The documents are rendered from the Markdown files in `docs/`, which exist in English only. | Translate the three documents and review them with a native speaker. |
| K-009 | On Windows, installing into a deeply nested folder can fail with "No such file or directory" inside `.venv\Lib\site-packages\lxml\...`. | Windows limits paths to 260 characters unless long paths are enabled, and a dependency of the SBOM tool ships deeply nested files. Found when testing a clean clone in a long temporary folder. | Clone into a short path (for example `C:\src\madkhal`) or enable long paths in Windows. |
