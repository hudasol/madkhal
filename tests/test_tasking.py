from __future__ import annotations

import copy
import datetime as dt
import math
import xml.etree.ElementTree as ET

import pytest

from madkhal.contract import ADVISORY_SCOPE, SIMULATION_NOTICE, DroneProfile
from madkhal.decision import SurveyConfig
from madkhal.estimator import SurveySensor
from madkhal.lab.inputs import snapshot
from madkhal.tasking import (
    MissionSpec,
    availability,
    geojson,
    kml,
    local_path,
    plan_mission,
    qgc_plan,
    validate_plan,
    wind_day,
)

SITE = snapshot().sites()[0]


@pytest.mark.req("MK-L6-001")
def test_survey_sensor_is_a_stated_assumption() -> None:
    cfg = SurveyConfig()
    s = cfg.sensor
    assert (s.p_clear, s.p_developing, s.p_at_intake) == (0.05, 0.6, 0.9)
    assert cfg.availability == 0.8 and cfg.cost_cu == 1000.0 and cfg.response_hours == 4.0
    with pytest.raises(ValueError):
        SurveySensor(p_clear=1.5)


@pytest.mark.req("MK-L6-002")
def test_mission_stays_within_radius_and_altitude() -> None:
    m = plan_mission(SITE)
    assert m.feasible and m.flight_time_s <= m.usable_time_s
    assert all(60 <= w.alt_m <= 120 for w in m.waypoints)
    pts = local_path(MissionSpec(), SITE.offshore_bearing_deg)
    spec = MissionSpec()
    reach = math.hypot(spec.radius_m, spec.width_m / 2)
    assert max(math.hypot(e, n) for e, n in pts) <= reach + 1e-6
    assert pts[0] == (0.0, 0.0) and pts[-1] == (0.0, 0.0)
    with pytest.raises(ValueError):
        DroneProfile(altitude_m=150)


@pytest.mark.req("MK-L6-003")
def test_mission_over_endurance_is_refused() -> None:
    m = plan_mission(SITE, MissionSpec(radius_m=8000, width_m=4000, line_spacing_m=400))
    assert not m.feasible
    assert m.refused_reason and "exceeds endurance" in m.refused_reason
    short = plan_mission(SITE, drone=DroneProfile(endurance_min=5))
    assert not short.feasible


@pytest.mark.req("MK-L6-004")
def test_windy_hours_are_unavailable() -> None:
    hours = wind_day("kalba", dt.date(2021, 7, 1), wind_limit_ms=8.0)
    assert len(hours) == 24
    for h in hours:
        assert h.available == (h.wind_ms <= 8.0)
    calm = availability(wind_day("kalba", dt.date(2021, 7, 1), 100.0))
    assert calm == 1.0
    assert 0.0 <= availability(hours) <= 1.0


@pytest.mark.req("MK-L6-005")
def test_exports_are_well_formed_and_the_plan_validates() -> None:
    m = plan_mission(SITE)
    plan = qgc_plan(m)
    assert validate_plan(plan) == []
    gj = geojson(m)
    assert gj["type"] == "FeatureCollection" and len(gj["features"]) == 3
    root = ET.fromstring(kml(m).encode("utf-8"))
    assert root.tag.endswith("kml")


@pytest.mark.req("MK-L6-005")
def test_validator_catches_broken_plans() -> None:
    plan = qgc_plan(plan_mission(SITE))
    for breaker in (
        lambda p: p.update(fileType="Mission"),
        lambda p: p["mission"]["items"].pop(0),
        lambda p: p["mission"]["items"][1].update(Altitude=300),
        lambda p: p["madkhal"].update(notice="cleared to fly"),
        lambda p: p["madkhal"].pop("scope"),
    ):
        broken = copy.deepcopy(plan)
        breaker(broken)
        assert validate_plan(broken) != []


@pytest.mark.req("MK-L6-006")
def test_every_export_carries_the_simulation_notice() -> None:
    m = plan_mission(SITE)
    assert m.notice == SIMULATION_NOTICE
    assert geojson(m)["properties"]["notice"] == SIMULATION_NOTICE
    assert all(f["properties"]["notice"] == SIMULATION_NOTICE for f in geojson(m)["features"])
    assert SIMULATION_NOTICE.replace("'", "&apos;") in kml(m) or SIMULATION_NOTICE in kml(m)
    assert qgc_plan(m)["madkhal"]["notice"] == SIMULATION_NOTICE
    # the advisory scope statement travels with every export too
    assert all(f["properties"]["scope"] == ADVISORY_SCOPE for f in geojson(m)["features"])
    assert ADVISORY_SCOPE in kml(m)
    assert qgc_plan(m)["madkhal"]["scope"] == ADVISORY_SCOPE


@pytest.mark.req("MK-L6-005")
@pytest.mark.req("MK-L6-006")
def test_plan_command_writes_three_exports_with_the_notice(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from typer.testing import CliRunner

    from madkhal.cli import app

    res = CliRunner().invoke(app, ["plan", "--site", "barka", "--out", str(tmp_path)])
    assert res.exit_code == 0, res.output
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == ["barka.geojson", "barka.kml", "barka.plan"]
    for name in files:
        text = (tmp_path / name).read_text(encoding="utf-8")
        assert SIMULATION_NOTICE in text
        assert ADVISORY_SCOPE in text
    bad = CliRunner().invoke(app, ["plan", "--site", "nowhere", "--out", str(tmp_path)])
    assert bad.exit_code != 0
