"""Manifest check: every snapshot file must match its recorded SHA-256."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from madkhal.core.errors import SnapshotError
from madkhal.core.jsonio import read_json, sha256_file

PINNED_COMMIT = "ca484e231943bf16262937dd727c6408a629a704"
SOURCE_REPOSITORY = "https://github.com/hudasol/nadhir"
MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024


def load_manifest(root: Path) -> dict[str, Any]:
    path = root / "MANIFEST.json"
    if not path.is_file():
        raise SnapshotError("MANIFEST.json", "manifest is missing")
    data: dict[str, Any] = read_json(path)
    if data.get("source_commit") != PINNED_COMMIT:
        raise SnapshotError("MANIFEST.json", f"source_commit is not the pinned {PINNED_COMMIT}")
    return data


def verify(root: Path) -> dict[str, Any]:
    """Raise SnapshotError naming the first file whose bytes differ from the manifest."""
    data = load_manifest(root)
    listed = set()
    total = 0
    for entry in data["files"]:
        rel = str(entry["path"])
        listed.add(rel)
        path = root / rel
        if not path.is_file():
            raise SnapshotError(rel, "listed in MANIFEST.json but missing")
        digest = sha256_file(path)
        if digest != entry["sha256"]:
            raise SnapshotError(
                rel, f"SHA-256 {digest[:12]} differs from manifest {str(entry['sha256'])[:12]}"
            )
        total += path.stat().st_size
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and rel != "MANIFEST.json" and rel not in listed:
            raise SnapshotError(rel, "file is not listed in MANIFEST.json")
    if total > MAX_SNAPSHOT_BYTES:
        raise SnapshotError("MANIFEST.json", f"snapshot is {total} bytes, above the 10 MB limit")
    return data
