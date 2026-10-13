# ADR 0011: MapLibre with local GeoJSON and no tile service

**Status:** accepted (P9).

## Context

The Inspection screen shows the estimated intake, the 25, 50 and 100 km watch zones and the
survey path. A base map would usually come from a tile provider. The hard constraints rule
that out: no paid service, no runtime network call other than the product's own API, and the
static demo must run on a free host with no backend.

## Decision

1. **MapLibre GL JS** (BSD licence) draws the map from an inline style with GeoJSON sources
   only. There is no tile source, no glyph server and no sprite; labels are HTML markers.
2. **Coastline.** `scripts/fetch_coastline.py` downloads the Natural Earth 1:50m coastline
   (public domain, pinned release v5.1.2) once, clips it to the study area and writes
   `web/public/geo/coastline.geojson` (under 4 kB), which is committed. The app reads it from
   its own origin. The map credits Natural Earth.
3. **Schematic, not survey grade.** The map is labelled schematic. The intake position is
   Nadhir's estimated coordinate and is shown as estimated.
4. **Accessible alternative.** The map is a labelled region; the same information (zone radii,
   path length, flight time) is given in text and tables beside it.

## Consequences

The map has no streets, bathymetry or satellite imagery. An end to end test records every
request on every screen and fails on any request outside the app's own origin, so a tile or
font request added later would be caught.
