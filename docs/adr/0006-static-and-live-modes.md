# ADR 0006: One web app, two modes (live API and static demo)

**Status:** accepted (P4).

## Context

The console should run against the live API during development and review, and also be
deployable on a free static host with no backend (no paid hosting, no server to maintain).

## Decision

1. **Live mode.** `madkhal serve` starts the FastAPI service on 127.0.0.1:8000. The web app
   calls relative paths under `/v1`; in development and preview Vite proxies `/v1` to the API.
2. **Static mode.** `madkhal snapshot` calls every GET route the console needs on the real
   API, in process, and writes each response as JSON under `web/public/api/` with the URL path
   as the file path (`/v1/sites` becomes `api/v1/sites.json`). `npm run build:static` builds the
   app with `__MADKHAL_MODE__ = "static"`, which makes the client read those files and ignore
   query parameters. Screens therefore use only the precomputed defaults in static mode; the
   console derives any date's belief from the precomputed daily series. Because the files are
   produced by the same API code, a test asserts each stored file equals the live response.
3. **Routing.** The app uses hash routing so any static host serves every screen from one
   `index.html` without rewrite rules.
4. **No other network call.** The client only fetches its own origin. Fonts are self hosted
   through `@fontsource`; there is no CDN, no analytics and no map tile request. A unit test
   scans the source for external URLs and an end to end test records every request in both
   modes.

## Consequences

The static snapshot is a generated artefact (`web/public/api/` is ignored by git) and must be
rebuilt whenever results change. Interactive features that need computation per request (the
Scenario Lab) use precomputed scenarios in static mode and say so on screen.
