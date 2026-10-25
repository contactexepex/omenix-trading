"""A session's realised variance from its 15-minute index levels (story A16; protocol v4's `RV_s`, design 5.2).

`RV_intraday` = sum over the 25 intervals between the 26 marks of the squared natural-log return; `RV_overnight` = the
squared log return from the previous session's 15:30 level to this session's 09:15 level; `RV_s` = their sum. Units:
squared log return of one session (a daily variance, dimensionless, not annualised); `vol_pct` = 100 * sqrt(RV_s), so
0.0001 is a 1.00% session. A part is void when any level it needs is missing or unusable: never interpolated. This is
a quote-snapshot measure, not a traded-price one. A new sampling rule is a new class with its own method name; the
candle-close back-fill (story A16b) is one, with the same arithmetic (`session_rv`, shared, never copied)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import pairwise

from .slots import MARKS_PER_SESSION

QUOTE_SNAPSHOT, CANDLE_CLOSE = "quote_snapshot", "candle_close"


@dataclass(frozen=True)
class RvResult:
    intraday: float | None
    overnight: float | None
    unusable_marks: tuple[int, ...]  # positions (0 = 09:15) whose level is missing or unusable
    previous_close_missing: bool

    @property
    def session(self) -> float | None:
        return None if self.intraday is None or self.overnight is None else self.intraday + self.overnight

    @property
    def vol_pct(self) -> float | None:
        return None if self.session is None else 100 * math.sqrt(self.session)


class IntradayRealisedVol(ABC):
    method: str
    measure: str

    @abstractmethod
    def compute(self, levels: list[float | None], previous_close: float | None) -> RvResult:
        """`levels`: the session's usable index level at each mark, None where unusable; `previous_close`: the
        previous session's usable 15:30 level, or None."""


class QuoteSnapshotRv15m(IntradayRealisedVol):
    method, measure = "rv-quote-15m-v1", QUOTE_SNAPSHOT

    def compute(self, levels: list[float | None], previous_close: float | None) -> RvResult:
        return session_rv(levels, previous_close)


class CandleCloseRv15m(IntradayRealisedVol):
    """Story A16b: the same 26 marks from Groww's 15-minute candles (the 09:15 open, then each candle's close)."""

    method, measure = "rv-candle-15m-v1", CANDLE_CLOSE

    def compute(self, levels: list[float | None], previous_close: float | None) -> RvResult:
        return session_rv(levels, previous_close)


def session_rv(levels: list[float | None], previous_close: float | None) -> RvResult:
    """A16's arithmetic, one function for every sampling rule."""
    if len(levels) != MARKS_PER_SESSION:
        raise ValueError(f"need {MARKS_PER_SESSION} levels, got {len(levels)}")
    unusable = tuple(i for i, level in enumerate(levels) if level is None)
    intraday = None if unusable else sum(_squared_log_return(a, b) for a, b in pairwise(levels))
    first = levels[0]
    overnight = None if previous_close is None or first is None else _squared_log_return(previous_close, first)
    return RvResult(intraday, overnight, unusable, previous_close is None)


def _squared_log_return(before: float, after: float) -> float:
    return math.log(after / before) ** 2
