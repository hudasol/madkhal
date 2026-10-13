from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from madkhal.api.app import MAX_BODY_BYTES, create_app
from madkhal.api.static import build_static, static_file_for, static_routes
from madkhal.contract import BloomBelief, Site
from madkhal.core import paths

client = TestClient(create_app())
# A drive letter not preceded by another letter (so "https://" is not a path), or a home folder.
PATH_PATTERN = re.compile(r"((?<![A-Za-z])[A-Za-z]:(\\\\|/)|/home/|/Users/|\\\\Users\\\\)")


def test_path_pattern_catches_paths_not_urls() -> None:
    assert PATH_PATTERN.search('"C:/Users/x/madkhal/data"')
    assert PATH_PATTERN.search('"C:\\\\data"')
    assert PATH_PATTERN.search("/home/runner/work")
    assert not PATH_PATTERN.search("https://github.com/hudasol/nadhir")


def _no_paths(text: str) -> None:
    assert not PATH_PATTERN.search(text), "response contains a file system path"
    assert str(paths.repo_root()) not in text


@pytest.mark.req("MK-L7-001")
def test_openapi_is_versioned() -> None:
    res = client.get("/v1/openapi.json")
    assert res.status_code == 200
    spec = res.json()
    assert all(p.startswith("/v1/") for p in spec["paths"])
    assert "/v1/belief/{site}" in spec["paths"]


@pytest.mark.req("MK-L7-003")
def test_health() -> None:
    res = client.get("/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["banner"]["hypothetical"].startswith("Plant, drone and consequences")


@pytest.mark.req("MK-L7-003")
def test_sites_olci_and_modis() -> None:
    olci = [Site.model_validate(s) for s in client.get("/v1/sites").json()]
    assert [s.id for s in olci] == ["kalba", "barka", "alraha"]
    modis = client.get("/v1/sites", params={"dataset": "modis_v1"}).json()
    assert [s["id"] for s in modis] == ["kalba", "fujairah", "rak", "dibba"]


@pytest.mark.req("MK-L7-003")
def test_evidence_calendar() -> None:
    res = client.get("/v1/evidence/kalba")
    assert res.status_code == 200
    body = res.json()
    assert len(body["dates"]) == len(body["state"]) == 2137
    assert set(body["state"]) == {"clear", "nodata", "alert"}
    assert all(e["status_badge"] for e in body["events"])
    _no_paths(res.text)


@pytest.mark.req("MK-L7-003")
def test_track_record_counts() -> None:
    body = client.get("/v1/track-record").json()
    assert (body["n_dated"], body["n_observable"], body["n_detected"]) == (5, 3, 1)
    assert body["hit_rate"]["k"] == 1 and body["hit_rate"]["n"] == 3
    assert body["lead_time"]["n"] == 1


@pytest.mark.req("MK-L7-003")
def test_belief_and_series() -> None:
    res = client.get("/v1/belief/kalba", params={"date": "2018-09-08"})
    assert res.status_code == 200
    b = BloomBelief.model_validate(res.json())
    assert b.alert and [w.horizon_days for w in b.within] == [1, 3, 7]
    assert res.headers["etag"]
    s = client.get(
        "/v1/belief/kalba/series", params={"start": "2018-09-01", "end": "2018-09-10"}
    ).json()
    assert len(s["dates"]) == 10 and len(s["within_3"]["median"]) == 10
    assert all(
        lo <= m <= hi
        for lo, m, hi in zip(
            s["within_3"]["lo"], s["within_3"]["median"], s["within_3"]["hi"], strict=True
        )
    )


@pytest.mark.req("MK-L7-002")
@pytest.mark.parametrize(
    ("url", "status"),
    [
        ("/v1/belief/atlantis", 404),
        ("/v1/evidence/atlantis", 404),
        ("/v1/belief/kalba?date=2030-01-01", 422),
        ("/v1/belief/kalba?date=yesterday", 422),
        ("/v1/belief/kalba?horizon=5", 422),
        ("/v1/belief/kalba?draws=5", 422),
        ("/v1/belief/kalba?seed=-1", 422),
        ("/v1/evidence/kalba?radius=500", 422),
        ("/v1/nothing-here", 404),
    ],
)
def test_errors_are_problem_json(url: str, status: int) -> None:
    res = client.get(url)
    assert res.status_code == status
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert set(body) >= {"type", "title", "status", "detail"}
    assert body["status"] == status
    _no_paths(res.text)


@pytest.mark.req("MK-L7-007")
def test_request_size_limit() -> None:
    res = client.post(
        "/v1/health",
        content=b"x" * (MAX_BODY_BYTES + 1),
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 413
    assert res.headers["content-type"].startswith("application/problem+json")


@pytest.mark.req("MK-L7-007")
def test_bounded_inputs_and_idempotent_ids() -> None:
    a = client.get("/v1/belief/kalba", params={"date": "2019-03-01", "draws": 100, "seed": 3})
    b = client.get("/v1/belief/kalba", params={"date": "2019-03-01", "draws": 100, "seed": 3})
    assert a.headers["etag"] == b.headers["etag"] and a.json() == b.json()
    c = client.get("/v1/belief/kalba", params={"date": "2019-03-01", "draws": 100, "seed": 4})
    assert c.headers["etag"] != a.headers["etag"]
    assert client.get("/v1/belief/kalba", params={"draws": 5000}).status_code == 422


@pytest.mark.slow
@pytest.mark.req("MK-L7-007")
def test_no_file_paths_in_any_static_route() -> None:
    for route in static_routes():
        _no_paths(client.get(route).text)


@pytest.mark.slow
@pytest.mark.req("MK-L7-008")
def test_static_snapshot_matches_live_responses(tmp_path) -> None:  # type: ignore[no-untyped-def]
    build_static(tmp_path)
    for route in static_routes():
        stored = json.loads((tmp_path / static_file_for(route)).read_text(encoding="utf-8"))
        assert stored == client.get(route).json(), route
    index = json.loads((tmp_path / "v1" / "index.json").read_text(encoding="utf-8"))
    assert set(index["routes"]) == set(static_routes())
