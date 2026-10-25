"""The evening's facts about today beyond the verdict (story FL1-1f, the owner's 30-second rule of 23 Oct 2026): the
day's path, why there is no verdict, and the record with live and back-tested checks apart. Values only; the words
are `verdict_words.py`'s."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .model import CLOSE_NOT_READ, DayShape, Outcome, TrackRecord

BACKTEST_WINDOW = 30  # the page's window: the back-test counts within the last 30 sessions; the light, 30 live ones
NO_FORECAST_WHY = "the {issued} 15:45 issue holds no next-session forecast for {day}"


def day_shape(levels: dict[str, float], previous_close: float | None) -> DayShape:
    return DayShape(levels.get("open"), levels.get("high"), levels.get("low"), previous_close)


def track_record(points: Sequence[Outcome]) -> TrackRecord:
    """`points`: one method's next-session checks, oldest first, today's own check last when there is one."""
    live, window = [p for p in points if p.live], points[-BACKTEST_WINDOW:]
    tested = [p for p in window if not p.live]
    return TrackRecord(len(live), sum(p.inside_90 for p in live), len(tested), sum(p.inside_90 for p in tested),
                       len(window), sum(p.inside_90 for p in live[-BACKTEST_WINDOW:]))  # fmt: skip


def unchecked_why(unchecked: str, close_why: str, issued: date, day: date) -> str:
    """The cause of no verdict in words: the close reader's own reason, or the issue that holds no forecast."""
    if unchecked == CLOSE_NOT_READ:
        return close_why
    return NO_FORECAST_WHY.format(issued=f"{issued:%a %d %b}", day=f"{day:%a %d %b}") if unchecked else ""
