# Status

What works today, in plain words.

- The repository skeleton exists: nine layer packages, a command line tool `madkhal`, and a
  fast check (`madkhal check`) that runs lint, strict type checks, layer import contracts,
  the requirement traceability check, the claims register check and the unit tests.
- The L0 contract exists: 27 typed models with English and Arabic field descriptions, from which
  the JSON Schema, the TypeScript types for the web app and the field dictionary are generated.
- The evidence layer reads a pinned, hash checked snapshot of the Nadhir hindcast outputs
  (Sentinel 3 OLCI for Kalba, Barka and Al Raha, 2018 to 2023; MODIS Aqua for four sites,
  2003 to 2014). It builds the daily coverage calendar (clear, nodata, alert) and the
  detector track record (5 dated events, 3 observable, 1 detected), and fails loudly on any
  altered or unexpected file.
- No estimator, plant model, decision engine, API or screen exists yet.

Evidence: real satellite history from the Nadhir hindcast. Plant, drone and consequences:
hypothetical, synthetic parameters.
