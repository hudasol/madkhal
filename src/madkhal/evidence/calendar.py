"""Coverage calendar: per site and day, clear, nodata or alert, with counted summaries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from madkhal.contract import CoverageState, EvidenceDay, RateWithCounts


@dataclass(frozen=True)
class CalendarCell:
    date: str
    state: str  # "clear", "nodata" or "alert"


def cell_state(day: EvidenceDay) -> str:
    if day.coverage == CoverageState.nodata:
        return "nodata"
    return "alert" if day.alert else "clear"


def calendar(days: Sequence[EvidenceDay]) -> list[CalendarCell]:
    return [CalendarCell(d.date.isoformat(), cell_state(d)) for d in days]


def monthly_clear_share(days: Sequence[EvidenceDay]) -> dict[int, RateWithCounts]:
    """Clear days over calendar days, per calendar month, pooled across years."""
    k = dict.fromkeys(range(1, 13), 0)
    n = dict.fromkeys(range(1, 13), 0)
    for d in days:
        n[d.date.month] += 1
        if d.coverage == CoverageState.clear:
            k[d.date.month] += 1
    return {
        m: RateWithCounts(
            k=k[m], n=n[m], rate=k[m] / n[m] if n[m] else None, note="clear of all days"
        )
        for m in range(1, 13)
    }


def yearly_counts(days: Sequence[EvidenceDay]) -> dict[int, dict[str, int]]:
    out: dict[int, dict[str, int]] = {}
    for d in days:
        row = out.setdefault(d.date.year, {"days": 0, "clear": 0, "alert": 0, "nodata": 0})
        row["days"] += 1
        if d.coverage == CoverageState.nodata:
            row["nodata"] += 1
        else:
            row["clear"] += 1
            row["alert"] += int(d.alert)
    return out
