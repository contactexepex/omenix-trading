"""The recorder's mark observer port (story A16; LM1, the position monitor, plugs in behind it). After each mark is
settled and its ledger row written, before the commit, the recorder tells the observer once per new row: the mark,
its ledger status (`status.py`'s strings, `missed` included) and this run's own snapshot document when it took that
mark (None otherwise: a missed or failed mark, or a copy another run stored). An observer failure is named by class
only (its text could carry a secret) and never stops the recorder's rows, alerts or commit."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from .document import SnapshotDocument, parse_time

OBSERVER_FAILED = "mark observer failed at {mark}: {error} (the recorder's rows and commit go ahead)"


class MembersFailed(Exception):
    """Some members of an observer group failed; `names` holds only class names and "timed out" (never a text)."""

    def __init__(self, names: list[str]):
        super().__init__()
        self.names = names


class MarkObserver(ABC):
    @abstractmethod
    def after_mark(self, day: date, mark: datetime, document: SnapshotDocument | None, status: str) -> None:
        """Called once per newly settled mark."""


class NoObserver(MarkObserver):
    def after_mark(self, day: date, mark: datetime, document: SnapshotDocument | None, status: str) -> None:
        return None


def notify(observer: MarkObserver, day: date, rows: list[dict], taken: SnapshotDocument | None) -> list[str]:
    """Tells the observer about each new ledger row; returns a line per observer failure."""
    lines = []
    for row in rows:
        mark = parse_time(row["mark"])
        document = taken if taken is not None and taken.mark == mark else None
        try:
            observer.after_mark(day, mark, document, row["status"])
        except Exception as exc:  # isolation: the class name only, and the recorder carries on
            error = ", ".join(exc.names) if isinstance(exc, MembersFailed) else type(exc).__name__
            lines.append(OBSERVER_FAILED.format(mark=row["mark_ist"], error=error))
    return lines
