"""Time conventions: dates and times are stored in UTC and shown in Asia/Dubai."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

UTC = dt.UTC
DISPLAY_TZ = ZoneInfo("Asia/Dubai")


def parse_date(text: str) -> dt.date:
    return dt.date.fromisoformat(text.strip())


def to_display(ts: dt.datetime) -> dt.datetime:
    if ts.tzinfo is None:
        raise ValueError("naive datetimes are not allowed; store UTC")
    return ts.astimezone(DISPLAY_TZ)


def day_of_year(d: dt.date) -> int:
    return d.timetuple().tm_yday
