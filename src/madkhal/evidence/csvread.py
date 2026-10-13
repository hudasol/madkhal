"""Validated CSV reading: exact headers and typed values, loud errors with file and column."""

from __future__ import annotations

import csv
import datetime as dt
import math
from collections.abc import Iterator
from pathlib import Path

from madkhal.core.errors import SnapshotError


class Row:
    """One data row with typed accessors that name the file, row and column on failure."""

    def __init__(self, file: str, index: int, values: dict[str, str]) -> None:
        self.file = file
        self.index = index  # 1 based data row (header excluded)
        self.values = values

    def _fail(self, column: str, message: str) -> SnapshotError:
        return SnapshotError(self.file, message, row=self.index, column=column)

    def raw(self, column: str) -> str:
        return self.values[column]

    def text(self, column: str, allowed: tuple[str, ...] | None = None) -> str:
        v = self.values[column]
        if allowed is not None and v not in allowed:
            raise self._fail(column, f"value {v!r} not in {allowed}")
        return v

    def integer(self, column: str, lo: int | None = None, hi: int | None = None) -> int:
        v = self.values[column]
        try:
            out = int(v)
        except ValueError:
            raise self._fail(column, f"expected an integer, got {v!r}") from None
        if (lo is not None and out < lo) or (hi is not None and out > hi):
            raise self._fail(column, f"integer {out} outside [{lo}, {hi}]")
        return out

    def number_or_none(
        self, column: str, lo: float | None = None, hi: float | None = None
    ) -> float | None:
        v = self.values[column]
        if v == "":
            return None
        try:
            out = float(v)
        except ValueError:
            raise self._fail(column, f"expected a number, got {v!r}") from None
        if math.isnan(out) or math.isinf(out):
            raise self._fail(column, f"non finite number {v!r}")
        if (lo is not None and out < lo) or (hi is not None and out > hi):
            raise self._fail(column, f"number {out} outside [{lo}, {hi}]")
        return out

    def number(self, column: str, lo: float | None = None, hi: float | None = None) -> float:
        out = self.number_or_none(column, lo, hi)
        if out is None:
            raise self._fail(column, "missing value")
        return out

    def boolean(self, column: str) -> bool:
        v = self.values[column]
        if v == "True":
            return True
        if v == "False":
            return False
        raise self._fail(column, f"expected True or False, got {v!r}")

    def date_or_none(self, column: str) -> dt.date | None:
        v = self.values[column]
        if v == "":
            return None
        try:
            return dt.date.fromisoformat(v)
        except ValueError:
            raise self._fail(column, f"expected an ISO date, got {v!r}") from None

    def date(self, column: str) -> dt.date:
        out = self.date_or_none(column)
        if out is None:
            raise self._fail(column, "missing date")
        return out


def read_rows(path: Path, display: str, expected: list[str]) -> Iterator[Row]:
    """Yield validated rows. The header must equal ``expected`` (same names, same order)."""
    if not path.is_file():
        raise SnapshotError(display, "file is missing")
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            raise SnapshotError(display, "file is empty") from None
        missing = [c for c in expected if c not in header]
        extra = [c for c in header if c not in expected]
        if missing:
            raise SnapshotError(display, "expected column is missing", column=missing[0])
        if extra:
            raise SnapshotError(display, "unexpected column", column=extra[0])
        if header != expected:
            raise SnapshotError(display, f"columns out of order: {header}")
        for i, values in enumerate(reader, start=1):
            if len(values) != len(header):
                raise SnapshotError(
                    display, f"expected {len(header)} fields, got {len(values)}", row=i
                )
            yield Row(display, i, dict(zip(header, values, strict=True)))
