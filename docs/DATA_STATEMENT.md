# Data statement

## Real data

* **Source.** Outputs of the Nadhir hindcast (https://github.com/hudasol/nadhir) at commit
  `ca484e231943bf16262937dd727c6408a629a704`: daily watch zone states, alert episodes, coverage
  per year, held out false alarm counts, event lead times, activity over documented periods,
  provenance files and the frozen detector configurations. 41 files, copied from git blobs into
  `data/nadhir_snapshot/` with a SHA-256 per file in `MANIFEST.json` (ADR 0002).
* **Underlying satellite data** (processed by Nadhir, not by Madkhal): Sentinel 3 OLCI Level 2
  full resolution chlorophyll (ESA and EUMETSAT, via the AWS Open Data Registry mirror) and
  MODIS Aqua Level 3 daily chlorophyll (NASA OBPG via NOAA CoastWatch ERDDAP). Licences and
  attributions are those recorded by Nadhir.
* **Events.** Eight documented bloom related events with Nadhir's evidence statuses, kept
  verbatim. Most dates are UNVERIFIED news report dates (upper bounds on onset); all coordinates
  are ESTIMATED town or plant positions, not surveyed intakes.
* **Coastline.** Natural Earth 1:50m coastline (public domain), clipped to the study area
  (`scripts/fetch_coastline.py`).

## Synthetic data

* The plant profile, the drone sensor, the wind hours, the costs, the policy lab worlds (G1,
  G2) and the Scenario Lab scenarios. All are labelled synthetic or hypothetical wherever they
  appear.
* Test fixtures in `tests/` and `web/src/test/` are hand made and labelled as synthetic.

## Personal data

None is needed, collected or stored. The snapshot contains organisation and place names in its
original text; Madkhal shows places and dates only (DECISIONS D-005).

## Known gaps

No operator data of any kind. No ground truth for bloom presence at the intakes beyond the
documented events. No sea temperature, current or wind data.
