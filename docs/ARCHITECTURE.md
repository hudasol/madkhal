# Architecture

Madkhal is nine layers plus a cross cutting core. Dependencies point downward only, and
import-linter contracts in `madkhal check` fail the build on a violation (`pyproject.toml`).
Evidence: real satellite history from the Nadhir hindcast. Plant, drone and consequences:
hypothetical, synthetic parameters. Advisory only: nothing here connects to a plant system.

## Layers

```mermaid
flowchart TB
  L8["L8 Presentation: web/ (React, TypeScript)<br/>operator console, i18n, accessibility"]
  L7["L7 Service: madkhal.api (FastAPI)<br/>/v1, problem+json, static snapshot"]
  L6["L6 Tasking: madkhal.tasking<br/>survey missions, exports"]
  L5["L5 Policy lab: madkhal.lab<br/>generators, policies, experiments, replay"]
  L4["L4 Decision: madkhal.decision<br/>risk table, feasibility, dwell, value of information"]
  L3["L3 Plant: madkhal.plant<br/>hypothetical SWRO unit"]
  L2["L2 Estimator: madkhal.estimator<br/>coverage aware Bayesian filter"]
  L1["L1 Evidence: madkhal.evidence<br/>the only reader of the Nadhir snapshot"]
  L0["L0 Contract: madkhal.contract<br/>pydantic models, generated schema and types"]
  X["X Core: madkhal.core<br/>paths, errors, determinism, JSON, traceability, claims"]
  L8 -->|HTTP or static JSON| L7
  L7 --> L6 --> L5 --> L4 --> L3 --> L2 --> L1 --> L0 --> X
```

Two contracts are enforced: the layer order above (the CLI sits on top of the API), and a
forbidden import contract that stops the estimator, plant, decision, contract and core layers
from importing the evidence layer, so that only L1 and the layers above it can reach the data.

## Data flow: from Nadhir files to an advisory and a mission

```mermaid
flowchart LR
  N["Nadhir outputs at commit ca484e2<br/>(zone_daily, false_alarms, lead times, events)"]
  S["data/nadhir_snapshot/<br/>41 files + MANIFEST.json (SHA-256)"]
  A["L1 NadhirSnapshot<br/>validated EvidenceDay, Event, TrackRecord"]
  P["L5 inputs: PriorSpec<br/>counts cited to file and row"]
  F["L2 filter over 400 draws<br/>belief per day with intervals"]
  D["L4 decision<br/>risk table, chance constraints"]
  PL["L3 hypothetical plant<br/>(assumption parameters)"]
  ADV["Advisory<br/>action, reasons, explanation, inputs hash"]
  V["L4 value of information"]
  M["L6 survey mission<br/>GeoJSON, KML, .plan"]
  N -->|scripts/refresh_nadhir_snapshot.py| S --> A --> P --> F --> D
  PL --> D --> ADV
  D --> V -->|INSPECT| M
```

## Deployment: live mode and static demo

```mermaid
flowchart LR
  subgraph live["Live mode (development, review)"]
    B1["Browser"] -->|"/v1 via Vite proxy"| API["madkhal serve<br/>uvicorn on 127.0.0.1:8000"]
    API --> SNAP1["data/nadhir_snapshot"]
  end
  subgraph static["Static demo (free static host)"]
    B2["Browser"] --> HOST["web/dist<br/>index.html, assets, api/v1/*.json"]
  end
  BUILD["madkhal snapshot<br/>calls every GET route in process"] --> HOST
```

The static files are produced by calling the real API in process, so the two modes cannot
drift apart (ADR 0006). The web app makes no request outside its own origin: fonts are self
hosted and the map uses local GeoJSON only, with no tile service.

## Sequence: a decision request

```mermaid
sequenceDiagram
  participant UI as Console (L8)
  participant API as API (L7)
  participant LAB as Replay (L5)
  participant EST as Estimator (L2)
  participant DEC as Decision (L4)
  participant PL as Plant (L3)
  UI->>API: GET /v1/advisory/kalba?date=2018-09-11
  API->>API: validate inputs (bounded, problem+json on error)
  API->>LAB: advisory_for(site, day)
  LAB->>EST: belief series (cached), posterior on the day
  LAB->>DEC: DecisionInputs (belief, transitions, profile, state, limits, seed)
  DEC->>PL: simulate draws x start states x candidates (72 hours)
  PL-->>DEC: breach, unserved water, breach hour
  DEC->>DEC: monotone envelope, feasibility, dwell, hysteresis
  DEC-->>API: Advisory (explanation object, plain text, inputs hash)
  API-->>UI: JSON
```

## Cross cutting rules

* **Contract first.** `madkhal.contract` is the single source of truth; JSON Schema
  (`contract/madkhal.schema.json`), TypeScript types (`web/src/contract/types.ts`) and the
  bilingual field dictionary are generated, and a test fails when they are stale.
* **Determinism.** Every random step draws from `substream(seed, label)`. Same inputs and seed
  give identical outputs; advisories carry the SHA-256 of their inputs as their id.
* **Pure core, thin edges.** File I/O lives in L1, the CLI and the API; the estimator, plant,
  decision and lab logic are pure functions of their inputs.
* **Traceability and claims.** `docs/requirements.yaml` and `docs/claims.yaml` are checked by
  `madkhal check`; the rendered matrices are `docs/TRACEABILITY.md` and `docs/CLAIMS.md`.
