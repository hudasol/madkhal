"""Hypothetical hourly wind for drone availability. SYNTHETIC, not a forecast.

ASSUMPTION: a daily sea breeze (calm at night, strongest in the mid afternoon) on top of a
monthly base, with seeded day to day noise. Used only to show which hours a survey could fly;
real operations would use a forecast service.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

from madkhal.core.determinism import substream

MONTHLY_BASE_MS = (5.0, 5.0, 5.5, 5.0, 5.0, 6.5, 6.5, 6.0, 5.0, 4.5, 4.5, 5.0)
SEA_BREEZE_MS = 4.0
DAYLIGHT_HOURS_LOCAL = range(6, 18)


@dataclass(frozen=True)
class HourWind:
    hour_local: int
    wind_ms: float
    available: bool


def wind_day(site: str, day: dt.date, wind_limit_ms: float) -> list[HourWind]:
    rng = substream(int(day.toordinal()), f"tasking.wind.{site}")
    day_factor = 1.0 + 0.35 * float(rng.standard_normal())
    base = MONTHLY_BASE_MS[day.month - 1]
    out = []
    for h in range(24):
        breeze = (
            SEA_BREEZE_MS * max(0.0, math.sin(math.pi * (h - 9) / 10.0)) if 9 <= h <= 19 else 0.0
        )
        w = max(0.0, (base + breeze) * day_factor + 0.8 * float(rng.standard_normal()))
        out.append(HourWind(h, round(w, 2), w <= wind_limit_ms))
    return out


def availability(hours: list[HourWind]) -> float:
    """Share of daylight hours with wind under the limit."""
    day = [h for h in hours if h.hour_local in DAYLIGHT_HOURS_LOCAL]
    return sum(h.available for h in day) / len(day) if day else 0.0
