"""Static snapshot: every API response the web app needs, written as JSON files.

The files mirror the URL paths (``/v1/sites`` becomes ``v1/sites.json``) so the web app can
run on a free static host with no backend. Responses are produced by calling the real API
in process, so the static and live modes cannot drift apart.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from madkhal.core.jsonio import dumps
from madkhal.lab.presets import SCENARIO_PRESETS

from .app import create_app
from .service import OLCI_SITES


def static_routes() -> list[str]:
    """Every GET path (with default query values) that the static demo serves."""
    routes = [
        "/v1/health",
        "/v1/sites",
        "/v1/track-record",
        "/v1/plant/profile",
        "/v1/plant/sensitivity",
        "/v1/policies/results",
        "/v1/method",
        "/v1/claims",
        "/v1/provenance",
    ]
    for s in OLCI_SITES:
        routes += [
            f"/v1/evidence/{s}",
            f"/v1/belief/{s}",
            f"/v1/belief/{s}/series",
            f"/v1/advisory/{s}",
            f"/v1/timeline/{s}",
            f"/v1/replay/{s}",
            f"/v1/missions/{s}",
        ]
    return routes


def static_file_for(route: str) -> str:
    return route.lstrip("/") + ".json"


def build_static(out_dir: Path, log: Callable[[str], None] = lambda _: None) -> list[Path]:
    client = TestClient(create_app())
    written = []
    index: dict[str, Any] = {"routes": {}}
    for route in static_routes():
        res = client.get(route)
        if res.status_code != 200:
            raise RuntimeError(f"{route} returned {res.status_code}: {res.text[:200]}")
        rel = static_file_for(route)
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(dumps(res.json(), indent=None).encode("utf-8"))
        index["routes"][route] = rel
        written.append(path)
        log(f"wrote {rel}")
    # The Scenario Lab cannot POST in static mode: precompute the presets through the same API.
    index["presets"] = {}
    for name, sc in SCENARIO_PRESETS.items():
        res = client.post("/v1/scenario/advise", json=sc.model_dump(mode="json"))
        if res.status_code != 200:
            raise RuntimeError(f"preset {name} returned {res.status_code}: {res.text[:200]}")
        rel = f"v1/scenario/presets/{name}.json"
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(dumps({**res.json(), "preset": name}, indent=None).encode("utf-8"))
        index["presets"][name] = rel
        written.append(path)
        log(f"wrote {rel}")
    idx = out_dir / "v1" / "index.json"
    idx.write_bytes(dumps(index).encode("utf-8"))
    written.append(idx)
    return written
