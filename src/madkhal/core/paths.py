"""Repository paths. Every file location used by Madkhal is resolved here."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Return the repository root.

    ``MADKHAL_ROOT`` wins when set. Otherwise walk up from this file until a
    directory holding ``pyproject.toml`` and ``data`` is found (editable install).
    """
    env = os.environ.get("MADKHAL_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "data").is_dir():
            return parent
    return Path.cwd().resolve()


def snapshot_dir() -> Path:
    return repo_root() / "data" / "nadhir_snapshot"


def docs_dir() -> Path:
    return repo_root() / "docs"


def results_dir() -> Path:
    return repo_root() / "results"


def contract_dir() -> Path:
    return repo_root() / "contract"


def web_dir() -> Path:
    return repo_root() / "web"
