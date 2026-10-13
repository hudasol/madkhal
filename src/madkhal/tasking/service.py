"""Inspection view for one site and day: mission, wind hours, value of a survey, exports."""

from __future__ import annotations

import datetime as dt
from typing import Any

from madkhal.contract import REPLAY_LABEL, SIMULATION_NOTICE, DroneProfile, Limits, PlantState, Site
from madkhal.decision import SurveyConfig, assess, from_estimator, risk_table
from madkhal.estimator import SurveySensor
from madkhal.lab.advise import _series, issued_at
from madkhal.plant import default_profile

from .exports import geojson, kml, qgc_plan, validate_plan
from .mission import MissionSpec, plan_mission
from .weather import availability, wind_day

DEFAULT_SORTIE_COST = 1000.0


def inspection_view(
    site: Site,
    day: dt.date,
    spec: MissionSpec | None = None,
    drone: DroneProfile | None = None,
    sortie_cost_cu: float = DEFAULT_SORTIE_COST,
    draws: int = 400,
    seed: int = 7,
) -> dict[str, Any]:
    dp = drone or DroneProfile()
    mission = plan_mission(site, spec, dp)
    hours = wind_day(site.id, day, dp.wind_limit_ms)
    avail = availability(hours)
    bs = _series(site.id, draws, seed)
    i = bs.index_of(day)
    inp = from_estimator(
        site.id,
        issued_at(day),
        bs.result.posterior[i],
        bs.draws,
        day.timetuple().tm_yday,
        default_profile(),
        PlantState(),
        Limits(),
        seed=seed,
        label=REPLAY_LABEL,
    )
    cfg = SurveyConfig(sensor=SurveySensor(), availability=avail, cost_cu=sortie_cost_cu)
    ins = assess(inp, risk_table(inp), cfg)
    plan = qgc_plan(mission)
    return {
        "label": REPLAY_LABEL,
        "notice": SIMULATION_NOTICE,
        "site": site.id,
        "date": day.isoformat(),
        "mission": mission.model_dump(mode="json"),
        "wind": [
            {"hour_local": h.hour_local, "wind_ms": h.wind_ms, "available": h.available}
            for h in hours
        ],
        "wind_note": "Hypothetical wind (assumption), not a forecast.",
        "availability": avail,
        "inspection": ins.model_dump(mode="json"),
        "sensor": SurveySensor().__dict__,
        "exports": {"geojson": geojson(mission), "kml": kml(mission), "plan": plan},
        "plan_valid": validate_plan(plan) == [],
    }
