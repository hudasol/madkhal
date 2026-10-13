"""Survey missions around an intake. For simulation and review only.

A lawnmower pattern covers a rectangle offshore of the estimated intake: lines parallel to the
coast, spaced ``line_spacing_m`` apart, from ``nearshore_m`` out to ``radius_m`` along the
assumed offshore bearing, ``width_m`` wide along the coast. The drone takes off at the intake,
flies the lines and returns. A mission whose flight time exceeds endurance less reserve is
refused, never trimmed silently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from madkhal.contract import SIMULATION_NOTICE, DroneProfile, Mission, Site, Waypoint
from madkhal.core.jsonio import inputs_hash

EARTH_M_PER_DEG = 111_320.0
CLIMB_RATE_MS = 2.0


@dataclass(frozen=True)
class MissionSpec:
    radius_m: float = 3000.0
    width_m: float = 1600.0
    line_spacing_m: float = 800.0
    nearshore_m: float = 200.0

    def __post_init__(self) -> None:
        if not 0 < self.nearshore_m < self.radius_m <= 20_000:
            raise ValueError("need 0 < nearshore_m < radius_m <= 20000")
        if not 100 <= self.line_spacing_m <= 5000:
            raise ValueError("line_spacing_m must be in [100, 5000]")
        if not 100 <= self.width_m <= 20_000:
            raise ValueError("width_m must be in [100, 20000]")


def to_latlon(lat0: float, lon0: float, east: float, north: float) -> tuple[float, float]:
    lat = lat0 + north / EARTH_M_PER_DEG
    lon = lon0 + east / (EARTH_M_PER_DEG * math.cos(math.radians(lat0)))
    return lat, lon


def local_path(spec: MissionSpec, bearing_deg: float) -> list[tuple[float, float]]:
    """Path in metres east and north of the intake, home first and last."""
    b = math.radians(bearing_deg)
    off = (math.sin(b), math.cos(b))  # offshore unit vector (east, north)
    along = (math.cos(b), -math.sin(b))  # along the coast
    pts: list[tuple[float, float]] = [(0.0, 0.0)]
    d = spec.nearshore_m
    k = 0
    half = spec.width_m / 2.0
    while d <= spec.radius_m + 1e-9:
        a0, a1 = (-half, half) if k % 2 == 0 else (half, -half)
        for a in (a0, a1):
            pts.append((off[0] * d + along[0] * a, off[1] * d + along[1] * a))
        d += spec.line_spacing_m
        k += 1
    pts.append((0.0, 0.0))
    return pts


def path_length(pts: list[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False))


def plan_mission(
    site: Site, spec: MissionSpec | None = None, drone: DroneProfile | None = None
) -> Mission:
    sp = spec or MissionSpec()
    dp = drone or DroneProfile()
    pts = local_path(sp, site.offshore_bearing_deg)
    dist = path_length(pts)
    flight = dist / dp.cruise_speed_ms + 2.0 * dp.altitude_m / CLIMB_RATE_MS
    usable = dp.endurance_min * 60.0 * (1.0 - dp.reserve_fraction)
    feasible = flight <= usable
    reason = None
    if not feasible:
        reason = (
            f"Flight time {flight / 60:.1f} min exceeds endurance less reserve "
            f"{usable / 60:.1f} min; reduce the radius or width or widen the line spacing."
        )
    wps = [
        Waypoint(lat=la, lon=lo, alt_m=dp.altitude_m)
        for la, lo in (to_latlon(site.lat, site.lon, e, n) for e, n in pts)
    ]
    key = {
        "site": site.id,
        "spec": sp.__dict__,
        "drone": dp.model_dump(),
        "bearing": site.offshore_bearing_deg,
    }
    return Mission(
        id=inputs_hash(key)[:16],
        site=site.id,
        radius_m=sp.radius_m,
        line_spacing_m=sp.line_spacing_m,
        drone=dp,
        waypoints=wps,
        distance_m=round(dist, 1),
        flight_time_s=round(flight, 1),
        usable_time_s=round(usable, 1),
        feasible=feasible,
        refused_reason=reason,
        notice=SIMULATION_NOTICE,
    )
