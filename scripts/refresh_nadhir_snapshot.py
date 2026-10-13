"""Copy the pinned Nadhir files into data/nadhir_snapshot/ and write MANIFEST.json.

Run once by a maintainer, from the repository root, with a Nadhir clone at the pinned
commit:

    python scripts/refresh_nadhir_snapshot.py --nadhir .sikka/refs/nadhir

The script refuses to run if the clone is not at the pinned commit. Files are copied
byte for byte; the manifest records the source path, the commit and a SHA-256 per file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PINNED_COMMIT = "ca484e231943bf16262937dd727c6408a629a704"
REPO = "https://github.com/hudasol/nadhir"

OLCI_SITES = ["kalba", "barka", "alraha"]
MODIS_SITES = ["kalba", "fujairah", "rak", "dibba"]
RADII = [25, 50, 100]
COMMON = [
    "zone_daily_r25.csv",
    "zone_daily_r50.csv",
    "zone_daily_r100.csv",
    "coverage.csv",
    "event_lead_times.csv",
    "false_alarms.csv",
    "period_activity.csv",
    "provenance.json",
]


def plan() -> list[tuple[str, str]]:
    """(source path inside Nadhir, destination path inside the snapshot)."""
    out = [
        ("events/events.yaml", "events.yaml"),
        ("config/nadhir.yaml", "config/nadhir.yaml"),
        ("config/frozen_detector_v1.yaml", "config/frozen_detector_v1.yaml"),
        ("config/frozen_detector_modis_v1.yaml", "config/frozen_detector_modis_v1.yaml"),
    ]
    for name in COMMON:
        out.append((f"outputs/frozen_detector_v1/{name}", f"olci_v1/{name}"))
        out.append((f"outputs/frozen_detector_modis_v1/{name}", f"modis_v1/{name}"))
    for site in OLCI_SITES:
        for r in RADII:
            n = f"episodes_{site}_r{r}.csv"
            out.append((f"outputs/frozen_detector_v1/{n}", f"olci_v1/{n}"))
    for site in MODIS_SITES:
        for r in RADII:
            n = f"episodes_{site}_r{r}.csv"
            out.append((f"outputs/frozen_detector_modis_v1/{n}", f"modis_v1/{n}"))
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nadhir", required=True, type=Path)
    ap.add_argument("--out", default=Path("data/nadhir_snapshot"), type=Path)
    args = ap.parse_args()
    head = subprocess.run(
        ["git", "-C", str(args.nadhir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if head != PINNED_COMMIT:
        print(f"Nadhir clone is at {head}, expected {PINNED_COMMIT}", file=sys.stderr)
        return 1
    files = []
    for src_rel, dst_rel in plan():
        dst = args.out / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Take the committed blob, not the working tree file, so line ending conversion
        # on checkout can never change the bytes or the hash.
        blob = subprocess.run(
            ["git", "-C", str(args.nadhir), "show", f"{PINNED_COMMIT}:{src_rel}"],
            capture_output=True,
            check=True,
        ).stdout
        dst.write_bytes(blob)
        files.append(
            {
                "path": dst_rel,
                "source_path": src_rel,
                "sha256": sha256(dst),
                "bytes": dst.stat().st_size,
                "gzipped": False,
            }
        )
    manifest = {
        "source_repository": REPO,
        "source_commit": PINNED_COMMIT,
        "note": (
            "Byte for byte copies of Nadhir outputs at the pinned commit. Real satellite "
            "evidence (Sentinel-3 OLCI 2018 to 2023, MODIS-Aqua 2003 to 2014). Do not edit; "
            "regenerate with scripts/refresh_nadhir_snapshot.py."
        ),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": sorted(files, key=lambda f: f["path"]),
    }
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    (args.out / "MANIFEST.json").write_bytes(text.encode("utf-8"))
    print(f"copied {len(files)} files, {manifest['total_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
