"""Fetch the Natural Earth 1:50m coastline (public domain) once, clip it to the study area and
write a small GeoJSON for the web map. Run by a maintainer; the result is committed so the app
never loads map data at runtime.

    python scripts/fetch_coastline.py

If the download fails after two retries, the script exits with a message and the map keeps its
schematic view (no coastline).
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_coastline.geojson"
BBOX = (51.0, 21.5, 60.5, 27.5)  # lon min, lat min, lon max, lat max
OUT = Path("web/public/geo/coastline.geojson")


def inside(p: list[float]) -> bool:
    return BBOX[0] <= p[0] <= BBOX[2] and BBOX[1] <= p[1] <= BBOX[3]


def clip(lines: list[list[list[float]]]) -> list[list[list[float]]]:
    out: list[list[list[float]]] = []
    for line in lines:
        cur: list[list[float]] = []
        for p in line:
            if inside(p):
                cur.append([round(p[0], 3), round(p[1], 3)])
            elif cur:
                if len(cur) > 1:
                    out.append(cur)
                cur = []
        if len(cur) > 1:
            out.append(cur)
    return out


def main() -> int:
    data = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(URL, timeout=60) as r:  # noqa: S310 (fixed public URL)
                data = json.loads(r.read().decode("utf-8"))
            break
        except Exception as exc:  # noqa: BLE001
            print(f"attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(2)
    if data is None:
        print("coastline not fetched; the map stays schematic", file=sys.stderr)
        return 1
    lines: list[list[list[float]]] = []
    for f in data["features"]:
        g = f["geometry"]
        if g["type"] == "LineString":
            lines.append(g["coordinates"])
        elif g["type"] == "MultiLineString":
            lines.extend(g["coordinates"])
    clipped = clip(lines)
    fc = {
        "type": "FeatureCollection",
        "properties": {
            "source": "Natural Earth 1:50m coastline v5.1.2 (public domain), clipped to the study area",
            "url": URL,
        },
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "MultiLineString", "coordinates": clipped},
            }
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes((json.dumps(fc, separators=(",", ":")) + "\n").encode("utf-8"))
    print(f"wrote {OUT} with {len(clipped)} lines, {OUT.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
