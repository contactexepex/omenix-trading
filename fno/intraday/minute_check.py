"""Each session's present levels checked against its own 1-minute candles (story A16b, orchestrator's decisions 55 and
62; an absent level needs no minute): the 09:15 open against the 09:15 minute's open, each close against the close of
the minute ending at the mark. Also gives the last pre-open 1-minute candle's close, NSE's official open by step 0 (114
of 114 sessions)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .candle_levels import Candle
from .slots import label, marks

TOLERANCE = 0.05  # points: one NIFTY tick
MINUTE = timedelta(minutes=1)


def beyond(difference: float) -> bool:
    """More than one tick apart; rounded first, so 0.05 in float arithmetic (0.0500000000007) is not beyond."""
    return round(abs(difference), 6) > TOLERANCE


@dataclass(frozen=True)
class MinuteCheck:
    mismatched: tuple[str, ...]  # marks (HH:MM) more than TOLERANCE from the 1-minute value
    missing: tuple[str, ...]  # minutes (HH:MM) the check needs and the answer lacks
    pre_open_close: float | None  # the last 1-minute candle starting before 09:15, if any


def check_minutes(day: date, levels: tuple[float | None, ...], minutes: list[Candle]) -> MinuteCheck:
    by_start = {c.start: c for c in minutes if c.start.date() == day}
    session_marks = marks(day)
    mismatched, missing = [], []
    for k, (mark, level) in enumerate(zip(session_marks, levels, strict=True)):
        if level is None:  # an absent level needs no minute (decision 62: only present marks are checked)
            continue
        start = mark if k == 0 else mark - MINUTE
        candle = by_start.get(start)
        if candle is None:
            missing.append(label(start))
            continue
        value = candle.open if k == 0 else candle.close
        if beyond(level - value):
            mismatched.append(label(mark))
    pre_open = [c for start, c in sorted(by_start.items()) if start < session_marks[0]]
    return MinuteCheck(tuple(mismatched), tuple(missing), pre_open[-1].close if pre_open else None)
