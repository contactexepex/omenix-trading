"""One dataset of dated raw NSE files and how to read a day's file: the building block the index-close reader and the
warm-up closes share (story A10). Raw files are only read; nothing here writes to Drive.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

NamedFile = tuple[str, bytes | None]  # (original file name, its bytes; None when no store or source has it)


class PanelBuildError(RuntimeError):
    """The panel is not research-ready: the listed days broke a rule. Nothing was written."""

    def __init__(self, problems: list[str]):
        super().__init__(f"{len(problems)} day(s) not research-ready:\n" + "\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class DailyFiles:
    """One dataset of dated raw files: its name in the exceptions file, the days it covers and how to get a day's
    file (wired in fno/storage/wiring.py from a `RawFileLibrary`: stores first, then NSE; never writes to Drive)."""

    label: str  # source_format for F&O files ("udiff", "legacy"); "index-close" for index closes
    dataset: str  # archive folder name, as in exceptions.csv
    first_day: date | None
    last_day: date | None
    get: Callable[[date], NamedFile]

    def covers(self, day: date) -> bool:
        return (self.first_day is None or day >= self.first_day) and (self.last_day is None or day <= self.last_day)
