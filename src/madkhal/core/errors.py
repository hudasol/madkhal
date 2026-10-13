"""Error types shared by every layer."""

from __future__ import annotations


class MadkhalError(Exception):
    """Base class for all Madkhal errors."""


class SnapshotError(MadkhalError):
    """The pinned Nadhir snapshot is missing, altered or malformed.

    The message always names the file, and the row and column when known.
    """

    def __init__(
        self, file: str, message: str, *, row: int | None = None, column: str | None = None
    ) -> None:
        self.file = file
        self.row = row
        self.column = column
        where = file
        if row is not None:
            where += f" row {row}"
        if column is not None:
            where += f" column '{column}'"
        super().__init__(f"{where}: {message}")


class InputError(MadkhalError):
    """A caller supplied an input outside its allowed range."""


class UnknownSiteError(InputError):
    """The requested site is not part of the evidence base."""
