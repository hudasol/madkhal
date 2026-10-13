# ADR 0002: A pinned Nadhir snapshot, read by one adapter

**Status:** accepted (P2).

## Context

Madkhal's evidence is the output of the Nadhir hindcast (https://github.com/hudasol/nadhir,
commit `ca484e231943bf16262937dd727c6408a629a704`). Depending on Nadhir as a package would
tie Madkhal to its code and its data pipeline; reading its files from many places would make
any change in them hard to detect.

## Decision

1. **Snapshot, do not depend.** `scripts/refresh_nadhir_snapshot.py` copies 41 files from the
   pinned commit into `data/nadhir_snapshot/` (4.35 MB in total, below the 10 MB limit, so no
   file is gzipped). The bytes are taken from the committed git blobs (`git show
   <commit>:<path>`), not from a working tree, so line ending conversion on checkout can never
   change them. `.gitattributes` marks the folder `-text` so Madkhal's own checkout keeps the
   bytes as well.
2. **Manifest.** `MANIFEST.json` records, per file, the snapshot path, the source path in
   Nadhir, the pinned commit, the byte size and the SHA-256. The adapter refuses to start if a
   listed file is missing, a hash differs, or an unlisted file is present. As an independent
   cross check, the SHA-256 of the snapshot's `events.yaml` equals the `events_sha256` that
   Nadhir recorded in both of its `provenance.json` files; a test asserts this.
3. **One adapter.** `madkhal.evidence.NadhirSnapshot` is the only code that reads the
   snapshot. An import-linter contract forbids the estimator, plant, decision, contract and
   core layers from importing the evidence layer, and a test fails if any other module refers
   to the snapshot folder. The claims register resolves `snapshot` pointers through a callback
   from the adapter.
4. **Fail loudly.** Every CSV header must equal the expected column list exactly (same names,
   same order). Every value is parsed with its type and range; consistency rules are checked.
   Errors are `SnapshotError` with a message of the form `<file> row <n> column '<name>':
   <problem>`.

## Schema found in the snapshot (inspected at the pinned commit)

| File | Columns | Rules enforced by the adapter |
|---|---|---|
| `{olci_v1,modis_v1}/zone_daily_r{25,50,100}.csv` | intake, date, n_obs, n_anom, max_z, median_logchl, month, n_clim, coverage, observed, anom_frac, state, radius_km | one row per site and consecutive day; month equals the date's month; radius equals the file's radius; n_anom at most n_obs; coverage in [0, 1]; state in NODATA, QUIET, EXCEED, ALERT; `observed` is False exactly when state is NODATA and exactly when anom_frac is empty; anom_frac in [0, 1] |
| `episodes_<site>_r<radius>.csv` | first_exceed, first_alert, last_exceed, closed_on, intake, radius_km | dates parse; first_exceed <= first_alert <= closed_on |
| `coverage.csv` | intake, radius_km, year, days, observed_days, observed_frac, median_gap_days, p90_gap_days, max_gap_days | observed_days at most days; a test checks the daily calendar reproduces observed_days for every OLCI site and year |
| `false_alarms.csv` | intake, radius_km, f_threshold, set, quiet_days, quiet_observed_days, alert_days, alert_day_rate_of_observed, alert_episodes_started, episodes_per_365_days, episodes_per_100_observed_days | alert_days at most quiet_observed_days; a test checks the adapter's quiet day rule reproduces quiet_days, quiet_observed_days and alert_days for all seven sites |
| `olci_v1/event_lead_times.csv` | the 13 base columns below plus first_exceed, first_alert, last_exceed, lead_alert_days, lead_alert_min_days, lead_first_exceed_days, last_quiet_before, lead_max_days, censored_at_data_start | outcome in DETECTED, MISS, NO-DATA; evaluation in EVALUATED, LIMITATION-TEST |
| `modis_v1/event_lead_times.csv` | event, evaluation, intake, radius_km, f_threshold, date_precision, evidence_status, t_ref, t_ref_earliest, lookback_start, days_in_lookback, obs_days_in_lookback, outcome | as above |
| `period_activity.csv` | event, evaluation, intake, radius_km, f_threshold, period, days, observed_days, exceed_or_alert_days, alert_days, max_anom_frac, median_anom_frac, alert_episodes_started, first_alert_in_period, first_exceed_in_period, evidence_status | counts are non negative integers |
| `events.yaml` | a top level `events` list | each event has id, intake_key, dataset, lat, lon, coord_status, date_precision, evidence_status and evaluation; every event id must have a neutral label in the adapter |
| `config/nadhir.yaml` | `intakes`, `periods`, `profiles.modis_v1` | used for estimated coordinates and the quiet period rule |
| `provenance.json` | detector, tag_commit, data, events_sha256, ... | the three named keys must exist |

## Readings made here

* **Observable.** Nadhir's results call two dated events "not observable" (RAK 2008 with one
  clear day and Dibba 2008 with none in the 121 day lookback) and score the other three. The
  adapter encodes this as "at least 5 clear days in the lookback at the 50 km radius". The
  observed counts are 33, 20 and 66 for the scored events and 1 and 0 for the others, so any
  threshold from 2 to 20 gives the same split: n_dated = 5, n_observable = 3, n_detected = 1.
* **Track record rows** are the `EVALUATED` rows of both `event_lead_times.csv` files at the
  50 km radius. The Al Raha row is Nadhir's `LIMITATION-TEST` and is reported as the species
  level blind spot, not as a miss in the hit rate.
* **Quiet days** follow Nadhir's own rule (held out year, extra quiet years, per site year
  exclusions, and 120 days before to 90 days after each dated event, inclusive).

## Consequences

A change in Nadhir reaches Madkhal only through a deliberate refresh, which changes the
manifest in a reviewable commit. The snapshot keeps Nadhir's text verbatim, including names
that Madkhal itself never displays (see `docs/DECISIONS.md` D-005).
