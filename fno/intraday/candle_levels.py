"""A session's 26 index levels from Groww's 15-minute candles (story A16b): the open of the 09:15 candle, then the close
of each candle ending at a mark (09:30 ... 15:30). These are A16's live rules (`candle_1m_open`, `candle_1m_close`) on
coarser candles: at the marks they give the same values. A missing candle leaves its level None, never filled."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .index_reading import candle_start
from .slots import MARK_STEP, marks

OPEN_BASIS, CLOSE_BASIS = "candle_15m_open", "candle_15m_close"
CANDLES_PER_SESSION = 25  # the candles starting 09:15 ... 15:15


class CandleParse(ValueError):
    """A candle row Groww's documented layout does not give (time with an offset, not a number, too short)."""


@dataclass(frozen=True)
class Candle:
    start: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class SessionCandles:
    levels: tuple[float | None, ...]  # 26, one per mark
    used: tuple[Candle, ...]  # the session's candles starting 09:15 ... 15:15 that were present
    missing: int  # of the 25
    outside: int  # candles of the day starting outside 09:15 ... 15:15 (pre-open, 15:30, 15:45 and later)

    @property
    def basis_counts(self) -> str:
        opens = int(self.levels[0] is not None)
        closes = sum(level is not None for level in self.levels[1:])
        return f"{OPEN_BASIS}:{opens};{CLOSE_BASIS}:{closes}"


def parse_candles(rows) -> list[Candle]:
    try:
        return [Candle(candle_start(str(r[0])), *(float(v) for v in r[1:5])) for r in rows]
    except (ValueError, TypeError, IndexError, KeyError) as exc:  # KeyError: a row that is a JSON object, not a list
        raise CandleParse(type(exc).__name__) from exc


def session_candles(day: date, candles: list[Candle]) -> SessionCandles:
    """The day's levels from any candles (others' days are ignored)."""
    starts = [m - MARK_STEP for m in marks(day)[1:]]  # 09:15 ... 15:15
    by_start = {c.start: c for c in candles if c.start.date() == day}
    used = tuple(by_start[s] for s in starts if s in by_start)
    first = by_start.get(starts[0])
    closes = [by_start[s].close if s in by_start else None for s in starts]
    levels = (first.open if first else None, *closes)
    outside = sum(1 for start in by_start if start not in set(starts))
    return SessionCandles(levels, used, CANDLES_PER_SESSION - len(used), outside)
