"""The index level and Groww's own time for it (story A16, Definitions "Index source time").

1. Primary: the index quote's `last_price` with its `last_trade_time` (epoch seconds, or milliseconds above 10^11).
2. Fallback, when Groww leaves that time empty (always, in the session of 15 Oct 2026): the level AND its time from
   one record, the latest finished 1-minute index candle: its close, and its end (start + 60 s). At the 09:15 mark no
   session candle has finished yet, so there the level is the open of the 09:15 candle and its time 09:15:00 (an open
   is fixed by the first trade; amendment 1). The quote's price is never used in fallback, so a frozen quote beside a
   live candle feed can never read as fresh. A forming candle's close is never used.
3. Neither: no time; the caller marks the level stale.

Candle start times are IST wall-clock text with no offset (step 0: `2026-10-14T09:15:00`); they are read as naive ISO
and given +05:30 explicitly, never the host's zone. A time that carries an offset, or does not parse, raises
ValueError (the caller names it `index_parse`)."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models import IST

QUOTE_BASIS, CANDLE_BASIS, OPEN_BASIS = "quote_last_trade_time", "candle_1m_close", "candle_1m_open"
CANDLE_SYMBOL = "NSE-NIFTY"
CANDLE_LOOKBACK = timedelta(minutes=5)
CANDLE_LENGTH = timedelta(minutes=1)
CANDLE_REQUEST_TIME = "%Y-%m-%d %H:%M:%S"
OPEN, CLOSE = 1, 4  # a candle row: start time, open, high, low, close, volume, open interest
MILLISECONDS_FROM = 10**11  # an epoch time above this is in milliseconds


def quote_reading(payload) -> tuple[float | None, datetime | None]:
    """The quote's level and its `last_trade_time` (None when Groww gives none)."""
    if not isinstance(payload, dict):
        return None, None
    level = payload.get("last_price")
    return (float(level) if level else None), epoch_time(payload.get("last_trade_time"))


def epoch_time(value) -> datetime | None:
    if not value:
        return None
    number = int(value)
    return datetime.fromtimestamp(number / 1000 if number > MILLISECONDS_FROM else number, IST)


def candle_window(received: datetime) -> dict:
    """The candle request's start and end times (IST text, as Groww takes them): the 5 minutes up to `received`."""
    local = received.astimezone(IST)
    return {
        "start_time": f"{local - CANDLE_LOOKBACK:{CANDLE_REQUEST_TIME}}",
        "end_time": f"{local:{CANDLE_REQUEST_TIME}}",
    }


def candle_reading(payload, received: datetime, mark: datetime) -> tuple[float | None, datetime | None, str]:
    """The level, its source time and the rule that gave them, from one candle:
    - the latest finished 1-minute candle's close and end, when it ends at or after the mark;
    - else, when the candle that starts at the mark is in the answer (the 09:15 mark: no session candle has finished
      yet), its open and its start: an open is fixed by the candle's first trade, at or after the mark (story A16
      amendment 1, in-session check of 15 Oct 2026);
    - else nothing (the caller marks the level stale; an older finished candle is left to the 120 s rule)."""
    rows = payload.get("candles") if isinstance(payload, dict) else None
    starts = [(candle_start(row[0]), row) for row in rows or []]
    finished = [(start + CANDLE_LENGTH, row) for start, row in starts if start + CANDLE_LENGTH <= received]
    latest = max(finished, key=lambda pair: pair[0]) if finished else None
    if latest and latest[0] >= mark:
        return float(latest[1][CLOSE]), latest[0], CANDLE_BASIS
    at_mark = [row for start, row in starts if start == mark]
    if at_mark:
        return float(at_mark[0][OPEN]), mark, OPEN_BASIS
    if latest:
        return float(latest[1][CLOSE]), latest[0], CANDLE_BASIS
    return None, None, ""


def candle_start(text: str) -> datetime:
    start = datetime.fromisoformat(text)
    if start.tzinfo is not None:
        raise ValueError("a candle time with an offset: the format changed, nothing is assumed")
    return start.replace(tzinfo=IST)
