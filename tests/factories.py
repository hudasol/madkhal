"""One valid instance of every contract model (synthetic test values, not data)."""

from __future__ import annotations

import datetime as dt
from typing import Any

from madkhal import contract as c


def interval(med: float = 0.1, lo: float = 0.05, hi: float = 0.2) -> c.Interval:
    return c.Interval(median=med, lo=lo, hi=hi, level=0.9)


def parameter(**kw: Any) -> c.Parameter:
    base: dict[str, Any] = {
        "key": "plant.k_foul",
        "label": "Fouling growth per unit breakthrough",
        "value": 0.05,
        "unit": "1/h",
        "evidence_level": "L0",
        "source": "assumption",
        "provenance": "ASSUMPTION for tests",
        "rel_spread": 0.3,
        "adverse": "up",
    }
    base.update(kw)
    return c.Parameter(**base)


def plant_profile() -> c.PlantProfile:
    return c.PlantProfile(
        id="test",
        name="Test plant",
        hypothetical=True,
        description="Synthetic test profile",
        parameters=[parameter(), parameter(key="plant.capacity", adverse="down")],
    )


def explanation() -> c.Explanation:
    return c.Explanation(
        belief_summary={"p_at_intake_3d": 0.1},
        plant_state=c.PlantState(),
        limits=c.Limits(),
        candidates=[
            c.CandidateEvaluation(
                action=c.ActionKind.GO,
                scale=1.0,
                p_fouling_breach=0.01,
                p_water_breach=0.0,
                expected_unserved_m3=0.0,
                feasible=True,
            )
        ],
        unconstrained_action=c.ActionKind.GO,
        unconstrained_scale=1.0,
        dwell_held=False,
        binding_constraint="fouling",
        evidence_level=c.EvidenceLevel.L0,
        assumption_share=1.0,
        n_samples=400,
        what_would_change=["A clear satellite view with an alert."],
    )


def advisory(**kw: Any) -> c.Advisory:
    base: dict[str, Any] = {
        "id": "abc",
        "site": "kalba",
        "issued_for": dt.datetime(2020, 1, 1, 6, tzinfo=dt.UTC),
        "action": c.ActionKind.GO,
        "scale": 1.0,
        "reasons": ["risk within budget"],
        "binding_constraint": "fouling",
        "p_breach_full_scale": 0.01,
        "time_to_limit_hours": None,
        "constraints": [
            c.ConstraintStatus(name="fouling", value=0.01, budget=0.05, used_percent=20.0)
        ],
        "evidence_level": c.EvidenceLevel.L0,
        "assumption_share": 1.0,
        "inspect": False,
        "inspect_reasons": [],
        "explanation": explanation(),
        "text": c.PlainText(
            what="Run at full scale.", why="Risk is within budget.", change="An alert."
        ),
        "inputs_hash": "abc",
        "seed": 7,
    }
    base.update(kw)
    return c.Advisory(**base)


def all_instances() -> list[Any]:
    rwc = c.RateWithCounts(k=1, n=3, rate=1 / 3, note="detected of observable")
    track_row = c.TrackRow(
        event_id="E2018-KALBA",
        label="Kalba 2018, desalination disruption report",
        dataset=c.Dataset.olci_v1,
        outcome="DETECTED",
        nadhir_outcome="DETECTED",
        clear_days_in_lookback=33,
        days_in_lookback=121,
        lead_alert_days=8.0,
        lead_alert_min_days=-6.0,
        evidence_status="UNVERIFIED",
        status_class=c.StatusClass.UNVERIFIED,
        source_file="olci_v1/event_lead_times.csv",
        source_row=1,
    )
    fa = c.FalseAlarmRow(
        site="kalba",
        dataset=c.Dataset.olci_v1,
        radius_km=50,
        alert_days=c.RateWithCounts(k=19, n=426, rate=19 / 426),
        episodes=5,
        quiet_days=830,
        episodes_per_year=2.2,
        source_file="olci_v1/false_alarms.csv",
        source_row=1,
    )
    return [
        c.Site(
            id="kalba",
            name="Kalba",
            name_ar="كلباء",
            dataset=c.Dataset.olci_v1,
            lat=25.05,
            lon=56.36,
            coord_status="ESTIMATED",
            offshore_bearing_deg=90,
            first_date=dt.date(2018, 1, 1),
            last_date=dt.date(2023, 11, 7),
            radii_km=[25, 50, 100],
            primary_radius_km=50,
        ),
        c.EvidenceDay(
            date=dt.date(2018, 9, 7),
            site="kalba",
            radius_km=50,
            coverage=c.CoverageState.clear,
            alert=True,
            detector_state=c.DetectorState.ALERT,
            anomaly_fraction=0.6,
            source_file="olci_v1/zone_daily_r50.csv",
            source_row=250,
        ),
        c.Event(
            id="E2018-KALBA",
            label="Kalba 2018, desalination disruption report",
            site="kalba",
            dataset=c.Dataset.olci_v1,
            lat=25.05,
            lon=56.36,
            coord_status="ESTIMATED",
            date_precision="day-of-report (upper bound)",
            t_ref=dt.date(2018, 9, 15),
            t_ref_earliest=dt.date(2018, 9, 1),
            evaluation="EVALUATED",
            evidence_status="UNVERIFIED",
            status_class=c.StatusClass.UNVERIFIED,
            status_badge="UNVERIFIED",
            source_file="events.yaml",
            source_index=6,
        ),
        rwc,
        track_row,
        fa,
        c.TrackRecord(
            n_dated=5,
            n_observable=3,
            n_detected=1,
            n_missed=2,
            n_not_observable=2,
            hit_rate=rwc,
            observable_rule="at least 5 clear days in the lookback",
            rows=[track_row],
            false_alarms=[fa],
            blind_spot_note="Al Raha 2023",
        ),
        interval(),
        c.HorizonProbability(horizon_days=3, p_at_intake=interval()),
        c.BeliefParameter(
            key="alpha",
            label="False alarm rate",
            value=interval(),
            source="nadhir",
            provenance="19 of 426",
        ),
        c.BloomBelief(
            site="kalba",
            date=dt.date(2018, 9, 7),
            p_clear=interval(0.8, 0.7, 0.9),
            p_developing=interval(),
            p_at_intake=interval(),
            p_any_bloom=interval(0.2, 0.1, 0.3),
            within=[
                c.HorizonProbability(horizon_days=h, p_at_intake=interval()) for h in (1, 3, 7)
            ],
            staleness_days=0,
            observation=c.CoverageState.clear,
            alert=True,
            n_draws=400,
            seed=7,
            parameters=[],
        ),
        parameter(),
        plant_profile(),
        c.Limits(),
        c.PlantState(),
        c.CandidateEvaluation(
            action=c.ActionKind.PARK,
            scale=0.0,
            p_fouling_breach=0.0,
            p_water_breach=0.2,
            expected_unserved_m3=100.0,
            feasible=False,
        ),
        c.ConstraintStatus(name="water_security", value=0.2, budget=0.05, used_percent=100.0),
        c.InspectAssessment(
            value_cu=10.0,
            sortie_cost_cu=5.0,
            break_even_cost_cu=10.0,
            availability=0.8,
            decision_could_change=True,
            inspect=True,
            reasons=["value exceeds cost"],
        ),
        explanation(),
        c.PlainText(what="a", why="b", change="c"),
        advisory(),
        c.Scenario(site="kalba", start_date=dt.date(2020, 8, 1), days=30, onset_day=5),
        c.MetricSummary(mean=1.0, lo=0.5, hi=1.5, unit="m3", n=30),
        c.PolicyResult(
            policy="P0",
            generator="G1",
            n_seeds=30,
            metrics={"unserved_m3": c.MetricSummary(mean=1.0, lo=0.5, hi=1.5, unit="m3", n=30)},
        ),
        c.Waypoint(lat=25.0, lon=56.4, alt_m=90),
        c.DroneProfile(),
        c.Mission(
            id="m1",
            site="kalba",
            radius_m=3000,
            line_spacing_m=800,
            drone=c.DroneProfile(),
            waypoints=[c.Waypoint(lat=25.0, lon=56.4, alt_m=90)],
            distance_m=10000,
            flight_time_s=833,
            usable_time_s=1200,
            feasible=True,
            notice=c.SIMULATION_NOTICE,
        ),
    ]
