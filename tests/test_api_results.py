from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from madkhal import cli
from madkhal.api.app import create_app
from madkhal.contract import SIMULATION_NOTICE
from madkhal.core import paths
from madkhal.tasking import validate_plan

client = TestClient(create_app())
HAVE_RESULTS = bool(cli.load_results(paths.repo_root()))
needs_results = pytest.mark.skipif(not HAVE_RESULTS, reason="results/*.json not generated yet")


@needs_results
@pytest.mark.req("MK-L7-005")
def test_policies_results_endpoint() -> None:
    body = client.get("/v1/policies/results").json()
    assert set(body) >= {"e1", "e2", "e3", "e4", "e5", "e6", "predictions", "run"}
    assert all(p["result"] in ("HIT", "MISS") for p in body["predictions"])


@needs_results
@pytest.mark.req("MK-L7-005")
def test_replay_endpoint() -> None:
    body = client.get("/v1/replay/kalba").json()
    assert body["label"].startswith("REPLAY")
    assert body["points"] and "quiet_non_go_per_year" in body
    assert client.get("/v1/replay/atlantis").status_code == 404


@pytest.mark.req("MK-L7-005")
def test_method_claims_and_provenance_endpoints() -> None:
    m = client.get("/v1/method").json()
    assert m["scope"].startswith("Advisory software")
    assert "native speaker" in m["arabic_note"]
    c = client.get("/v1/claims").json()
    assert {x["type"] for x in c["claims"]} <= set(c["types"])
    assert any(x["id"] == "CL-001" for x in c["claims"])
    p = client.get("/v1/provenance").json()
    assert p["evidence"]["source_commit"].startswith("ca484e2")
    assert len(p["evidence"]["files"]) == 41


@pytest.mark.req("MK-L7-006")
def test_missions_endpoint() -> None:
    res = client.get("/v1/missions/kalba", params={"date": "2018-09-08"})
    assert res.status_code == 200
    body = res.json()
    assert body["notice"] == SIMULATION_NOTICE
    assert body["mission"]["feasible"] is True
    assert validate_plan(body["exports"]["plan"]) == []
    assert len(body["wind"]) == 24
    assert body["inspection"]["value_cu"] >= 0
    big = client.get(
        "/v1/missions/kalba", params={"radius_m": 15000, "width_m": 8000, "spacing_m": 300}
    )
    assert big.status_code == 200 and big.json()["mission"]["feasible"] is False
    bad = client.get("/v1/missions/kalba", params={"altitude_m": 200})
    assert bad.status_code == 422
