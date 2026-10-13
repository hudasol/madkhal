"""Test configuration.

`madkhal check`, `madkhal all` and CI set MADKHAL_CHECK=1, which loads a derandomized
Hypothesis profile without the example database: the gate then gives the same answer on every
run. Plain `pytest` keeps Hypothesis's random search, which explores more inputs over time.
"""

from __future__ import annotations

import os

from hypothesis import settings

settings.register_profile("check", derandomize=True, database=None)
if os.environ.get("MADKHAL_CHECK") == "1":
    settings.load_profile("check")
