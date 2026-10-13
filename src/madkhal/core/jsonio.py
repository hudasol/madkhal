"""Canonical JSON: UTF-8, Arabic preserved, sorted keys, LF line endings."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _clean(obj: Any) -> Any:
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_clean(v) for v in obj]
    return obj


def dumps(obj: Any, *, indent: int | None = 2) -> str:
    text = json.dumps(_clean(obj), ensure_ascii=False, sort_keys=True, indent=indent)
    return text + "\n" if indent is not None else text


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps(obj).encode("utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def inputs_hash(obj: Any) -> str:
    """SHA-256 of the canonical compact JSON form of ``obj`` (an idempotent id)."""
    return hashlib.sha256(dumps(obj, indent=None).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()
