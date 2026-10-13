"""Mission exports: GeoJSON, KML and a QGroundControl .plan, each carrying the notice.

The .plan follows the QGroundControl plan file layout (fileType Plan, mission version 2,
SimpleItem commands: 22 takeoff, 16 waypoint, 20 return to launch). It has not been loaded in
QGroundControl in this project; ``validate_plan`` checks the structure only.
"""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape

from madkhal.contract import SIMULATION_NOTICE, Mission
from madkhal.core.jsonio import dumps

MAV_CMD_NAV_TAKEOFF = 22
MAV_CMD_NAV_WAYPOINT = 16
MAV_CMD_NAV_RETURN_TO_LAUNCH = 20
FRAME_RELATIVE_ALT = 3


def geojson(m: Mission) -> dict[str, Any]:
    line = [[w.lon, w.lat] for w in m.waypoints]
    home = m.waypoints[0]
    survey = m.waypoints[1:-1]
    ring = [[w.lon, w.lat] for w in survey] + ([[survey[0].lon, survey[0].lat]] if survey else [])
    props = {"notice": SIMULATION_NOTICE, "mission_id": m.id, "site": m.site}
    return {
        "type": "FeatureCollection",
        "properties": props,
        "features": [
            {
                "type": "Feature",
                "properties": {**props, "role": "home (estimated intake)"},
                "geometry": {"type": "Point", "coordinates": [home.lon, home.lat]},
            },
            {
                "type": "Feature",
                "properties": {**props, "role": "flight path", "altitude_m": home.alt_m},
                "geometry": {"type": "LineString", "coordinates": line},
            },
            {
                "type": "Feature",
                "properties": {**props, "role": "survey lines"},
                "geometry": {"type": "LineString", "coordinates": ring},
            },
        ],
    }


def kml(m: Mission) -> str:
    coords = " ".join(f"{w.lon:.6f},{w.lat:.6f},{w.alt_m:.0f}" for w in m.waypoints)
    home = m.waypoints[0]
    note = escape(SIMULATION_NOTICE)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        "<Document>\n"
        f"<name>Madkhal survey {escape(m.site)} {escape(m.id)}</name>\n"
        f"<description>{note}</description>\n"
        "<Placemark>\n<name>Home (estimated intake)</name>\n"
        f"<description>{note}</description>\n"
        f"<Point><coordinates>{home.lon:.6f},{home.lat:.6f},0</coordinates></Point>\n</Placemark>\n"
        "<Placemark>\n<name>Flight path</name>\n"
        f"<description>{note}</description>\n"
        "<LineString><altitudeMode>relativeToGround</altitudeMode>"
        f"<coordinates>{coords}</coordinates></LineString>\n</Placemark>\n"
        "</Document>\n</kml>\n"
    )


def _item(seq: int, cmd: int, lat: float, lon: float, alt: float) -> dict[str, Any]:
    return {
        "type": "SimpleItem",
        "autoContinue": True,
        "command": cmd,
        "doJumpId": seq,
        "frame": FRAME_RELATIVE_ALT,
        "params": [0, 0, 0, None, lat, lon, alt],
        "Altitude": alt,
        "AltitudeMode": 1,
        "AMSLAltAboveTerrain": None,
    }


def qgc_plan(m: Mission) -> dict[str, Any]:
    home = m.waypoints[0]
    alt = m.drone.altitude_m
    items = [_item(1, MAV_CMD_NAV_TAKEOFF, home.lat, home.lon, alt)]
    for i, w in enumerate(m.waypoints[1:-1], start=2):
        items.append(_item(i, MAV_CMD_NAV_WAYPOINT, w.lat, w.lon, alt))
    rtl = _item(len(items) + 1, MAV_CMD_NAV_RETURN_TO_LAUNCH, 0.0, 0.0, 0.0)
    rtl["params"] = [0, 0, 0, 0, 0, 0, 0]
    items.append(rtl)
    return {
        "fileType": "Plan",
        "version": 1,
        "groundStation": "QGroundControl",
        "mission": {
            "version": 2,
            "firmwareType": 12,
            "vehicleType": 2,
            "cruiseSpeed": m.drone.cruise_speed_ms,
            "hoverSpeed": 5,
            "plannedHomePosition": [home.lat, home.lon, 0],
            "items": items,
        },
        "geoFence": {"version": 2, "circles": [], "polygons": []},
        "rallyPoints": {"version": 2, "points": []},
        "madkhal": {"notice": SIMULATION_NOTICE, "mission_id": m.id, "feasible": m.feasible},
    }


def validate_plan(plan: dict[str, Any]) -> list[str]:
    """Structural problems of a .plan (empty list when it is well formed)."""
    errs: list[str] = []
    if plan.get("fileType") != "Plan":
        errs.append("fileType must be Plan")
    if plan.get("version") != 1:
        errs.append("version must be 1")
    if plan.get("groundStation") != "QGroundControl":
        errs.append("groundStation must be QGroundControl")
    mission = plan.get("mission")
    if not isinstance(mission, dict):
        return errs + ["mission object missing"]
    if mission.get("version") != 2:
        errs.append("mission.version must be 2")
    home = mission.get("plannedHomePosition")
    if not (
        isinstance(home, list) and len(home) == 3 and all(isinstance(x, int | float) for x in home)
    ):
        errs.append("plannedHomePosition must be [lat, lon, alt]")
    items = mission.get("items")
    if not isinstance(items, list) or len(items) < 3:
        return errs + ["mission.items must hold takeoff, waypoints and return"]
    for i, it in enumerate(items):
        if it.get("type") != "SimpleItem":
            errs.append(f"item {i}: type must be SimpleItem")
        if not isinstance(it.get("command"), int):
            errs.append(f"item {i}: command must be an integer")
        p = it.get("params")
        if not (isinstance(p, list) and len(p) == 7):
            errs.append(f"item {i}: params must have 7 entries")
        if it.get("doJumpId") != i + 1:
            errs.append(f"item {i}: doJumpId must be {i + 1}")
    if items[0].get("command") != MAV_CMD_NAV_TAKEOFF:
        errs.append("first item must be a takeoff")
    if items[-1].get("command") != MAV_CMD_NAV_RETURN_TO_LAUNCH:
        errs.append("last item must return to launch")
    for i, it in enumerate(items[:-1]):
        alt = it.get("Altitude")
        if not (isinstance(alt, int | float) and 60 <= alt <= 120):
            errs.append(f"item {i}: altitude must be within 60 to 120 m")
        lat, lon = it["params"][4], it["params"][5]
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            errs.append(f"item {i}: coordinates out of range")
    for key in ("geoFence", "rallyPoints"):
        if not isinstance(plan.get(key), dict):
            errs.append(f"{key} missing")
    if plan.get("madkhal", {}).get("notice") != SIMULATION_NOTICE:
        errs.append("simulation only notice missing")
    return errs


def plan_text(m: Mission) -> str:
    return dumps(qgc_plan(m))
