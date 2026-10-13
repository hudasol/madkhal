from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from madkhal.api.app import create_app
from madkhal.contract import REPLAY_LABEL, Advisory, Scenario
from madkhal.lab.advise import run_scenario, window_advice

client = TestClient(create_app())


@pytest.mark.req("MK-L7-004")
def test_advisory_endpoint() -> None:
    res = client.get("/v1/advisory/kalba", params={"date": "2018-09-11"})
    assert res.status_code == 200
    adv = Advisory.model_validate(res.json())
    assert adv.label == REPLAY_LABEL
    assert adv.action.value == "DERATE"
    assert adv.explanation.candidates and adv.text.what


@pytest.mark.req("MK-L7-004")
@pytest.mark.parametrize(
    ("params", "status"),
    [
        ({"profile": "real-plant"}, 404),
        ({"storage_hours": 500}, 422),
        ({"fouling_index": -1}, 422),
        ({"date": "1999-01-01"}, 422),
    ],
)
def test_advisory_rejects_bad_inputs(params: dict[str, object], status: int) -> None:
    res = client.get("/v1/advisory/kalba", params=params)
    assert res.status_code == status
    assert res.headers["content-type"].startswith("application/problem+json")


@pytest.mark.req("MK-L7-004")
def test_timeline_endpoint_window() -> None:
    res = client.get("/v1/timeline/kalba", params={"start": "2018-09-01", "end": "2018-09-20"})
    assert res.status_code == 200
    body = res.json()
    assert body["label"] == REPLAY_LABEL
    assert len(body["dates"]) == len(body["action"]) == 20
    assert "DERATE" in body["action"]
    too_long = client.get("/v1/timeline/kalba", params={"start": "2018-01-01", "end": "2019-12-31"})
    assert too_long.status_code == 422


@pytest.mark.req("MK-L7-004")
def test_plant_profile_and_sensitivity_endpoints() -> None:
    prof = client.get("/v1/plant/profile").json()
    assert prof["hypothetical"] is True and prof["assumption_share"] == 1.0
    sens = client.get("/v1/plant/sensitivity").json()
    assert sens["rows"][0]["rank"] == 1
    assert 1 <= len(sens["measure_first"]) <= 3


@pytest.mark.req("MK-L7-004")
def test_scenario_endpoint_and_size_limit() -> None:
    body = {
        "site": "kalba",
        "start_date": "2021-08-20",
        "days": 12,
        "onset_day": 2,
        "intensity": 1.5,
    }
    res = client.post("/v1/scenario/advise", json=body)
    assert res.status_code == 200
    out = res.json()
    assert out["label"].startswith("SCENARIO")
    assert len(out["days"]) == 12
    bad = client.post("/v1/scenario/advise", json={**body, "days": 1000})
    assert bad.status_code == 422


@pytest.mark.req("MK-L5-009")
def test_window_advice_is_causal() -> None:
    a = window_advice("barka", dt.date(2019, 3, 1), dt.date(2019, 3, 20))
    b = window_advice("barka", dt.date(2019, 3, 1), dt.date(2019, 4, 30))
    assert a == b[: len(a)]


@pytest.mark.req("MK-L5-008")
def test_scenario_is_deterministic() -> None:
    sc = Scenario(
        site="kalba", start_date=dt.date(2021, 8, 20), days=10, onset_day=1, intensity=2.0, seed=4
    )
    assert run_scenario(sc) == run_scenario(sc)
