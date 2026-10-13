"""Unit conventions and annotated scalar types.

UTC is stored, Asia/Dubai is used only for display. SI units; volumes in cubic metres
(m3), flow in cubic metres per hour (m3/h), percentages 0 to 100, probabilities 0 to 1.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from pydantic import AfterValidator, AwareDatetime, Field

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
Percent = Annotated[float, Field(ge=0.0, le=100.0)]
Fraction = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegative = Annotated[float, Field(ge=0.0)]


def _to_utc(value: dt.datetime) -> dt.datetime:
    return value.astimezone(dt.UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]

UNITS = {
    "probability": "1",
    "fraction": "1",
    "percent": "%",
    "volume": "m3",
    "flow": "m3/h",
    "hours": "h",
    "days": "d",
    "metres": "m",
    "kilometres": "km",
    "seconds": "s",
    "speed": "m/s",
    "degrees": "deg",
    "index": "1",
    "cost": "CU",
}


def fd(en: str, ar: str, unit: str | None = None, **kwargs: Any) -> Any:
    """A pydantic Field with an English description and an Arabic description.

    The Arabic text is machine drafted and should be reviewed by a native speaker.
    """
    extra: dict[str, Any] = {"x-ar": ar}
    if unit is not None:
        if unit not in UNITS.values():
            raise ValueError(f"unknown unit {unit!r}")
        extra["x-unit"] = unit
    return Field(description=en, json_schema_extra=extra, **kwargs)
