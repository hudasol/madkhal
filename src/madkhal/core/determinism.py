"""Determinism helpers: explicit seeds and stable hashing.

Every stochastic step in Madkhal takes a numpy Generator derived from an explicit
integer seed. Sub streams are derived from a seed and a text label so that adding a
new random step never shifts the random numbers of an existing one.
"""

from __future__ import annotations

import hashlib

import numpy as np

MAX_SEED = 2**31 - 1


def check_seed(seed: int) -> int:
    if not 0 <= int(seed) <= MAX_SEED:
        raise ValueError(f"seed must be in [0, {MAX_SEED}], got {seed}")
    return int(seed)


def substream(seed: int, label: str) -> np.random.Generator:
    """A Generator determined only by ``seed`` and ``label``."""
    check_seed(seed)
    digest = hashlib.sha256(f"{seed}:{label}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))
