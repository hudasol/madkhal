"""Scenario Lab presets (synthetic). Precomputed for the static demo."""

from __future__ import annotations

import datetime as dt

from madkhal.contract import Scenario

START = dt.date(2021, 8, 20)

SCENARIO_PRESETS: dict[str, Scenario] = {
    "visible_bloom": Scenario(
        site="kalba",
        start_date=START,
        days=30,
        onset_day=5,
        days_to_intake=4,
        duration_days=10,
        intensity=1.5,
        detector_availability=0.6,
        detector_visible=True,
        seed=7,
    ),
    "invisible_bloom": Scenario(
        site="kalba",
        start_date=START,
        days=30,
        onset_day=5,
        days_to_intake=4,
        duration_days=10,
        intensity=1.5,
        detector_availability=0.6,
        detector_visible=False,
        seed=7,
    ),
    "blind_season": Scenario(
        site="kalba",
        start_date=START,
        days=30,
        onset_day=5,
        days_to_intake=4,
        duration_days=10,
        intensity=1.5,
        detector_availability=0.15,
        detector_visible=True,
        seed=7,
    ),
    "quiet": Scenario(
        site="kalba",
        start_date=START,
        days=30,
        onset_day=None,
        intensity=0.0,
        detector_availability=0.6,
        detector_visible=True,
        seed=7,
    ),
}
