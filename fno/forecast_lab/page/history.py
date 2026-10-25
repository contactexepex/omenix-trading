"""Each method's recent record (story FL1-1c v2) from G13b's own score rows, never recomputed: one cell per session
(inside the 50% band, inside the 90% band, or no forecast), its coverage and error over the last 7, 14 and 30
sessions, and the 90% band's coverage over the trailing 20 sessions for the trend line."""

from __future__ import annotations

import statistics
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .model import Band, Cell, MethodRecord, Window

WINDOWS = (7, 14, 30)
ROLLING = 20  # sessions in the trend line's trailing window (the drift rule's too)


@dataclass(frozen=True)
class ScorePoint:
    """One G13b score row, in the page's terms, with the band it scored (None when its record is not on file)."""

    method: str
    horizon: str
    target_day: date
    close: float
    error_points: float  # G13b's quantile score times the close: index points
    inside_50: bool | None  # None for a point forecast (no band)
    inside_90: bool | None
    live: bool
    issue_day: date | None = None
    band: Band | None = None


class HistorySource(ABC):
    """Every scored forecast of an underlying: one per method, horizon and target day, a sealed live one preferred."""

    @abstractmethod
    def points(self, underlying: str) -> list[ScorePoint]: ...

    def targets(self, underlying: str, method: str, horizon: str) -> set[date]:
        """Every day a forecast by `method` at `horizon` was made for, live or back-filled, scored or not (FL1-1e: a
        day without one is a gap in the record, never a late score). Empty when the source cannot tell."""
        return set()


def _share(flags: Sequence[bool | None]) -> float | None:
    known = [f for f in flags if f is not None]
    return sum(known) / len(known) if known else None


def window(points: Sequence[ScorePoint], days: Sequence[date], sessions: int) -> Window:
    recent = set(days[-sessions:])
    chosen = [p for p in points if p.target_day in recent]
    error = statistics.fmean(p.error_points for p in chosen) if chosen else None
    return Window(sessions, len(chosen), _share([p.inside_50 for p in chosen]),
                  _share([p.inside_90 for p in chosen]), error)  # fmt: skip


def rolling_90(points: Sequence[ScorePoint], history: Sequence[date], shown: Sequence[date]) -> tuple:
    """The 90% band's coverage over the `ROLLING` sessions ending at each shown session (None while too few)."""
    by_day = {p.target_day: p.inside_90 for p in points}
    out = []
    for day in shown:
        trailing = [d for d in history if d <= day][-ROLLING:]
        flags = [by_day.get(d) for d in trailing]
        known = [f for f in flags if f is not None]
        out.append(sum(known) / len(known) if len(known) == ROLLING else None)
    return tuple(out)


def method_record(points: Sequence[ScorePoint], history: Sequence[date], shown: Sequence[date],
                  best: bool) -> MethodRecord:  # fmt: skip
    """`history`: every session with a known close, oldest first; `shown`: the grid's sessions (its tail)."""
    by_day = {p.target_day: p for p in points}
    cells = tuple(Cell(d, by_day[d].inside_50, by_day[d].inside_90, by_day[d].live) if d in by_day
                  else Cell(d, None, None, False) for d in shown)  # fmt: skip
    windows = tuple(window(points, history, n) for n in WINDOWS)
    return MethodRecord(points[0].method if points else "", cells, windows, rolling_90(points, history, shown), best)
