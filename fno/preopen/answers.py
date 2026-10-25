"""Pure readers of the three pre-open answers (story A22). Each returns a `Reading`: complete or not (and why), the
source's own time, and the day-row values. An answer not in its layout raises `BadAnswer` (a ValueError); "no data"
is never "complete"."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from ..intraday.candle_levels import Candle, CandleParse, parse_candles
from ..models import IST

GIFT_TIME, PREOPEN_TIME = "%d-%b-%Y %H:%M", "%d-%b-%Y %H:%M:%S"
GIFT_FRESH_FOR = timedelta(minutes=15)  # NSE's time at most this long before our seen_at
GIFT_AHEAD_ALLOWED = timedelta(minutes=1)  # NSE's time has minute resolution: up to a minute "ahead" is our clock
PREOPEN_FINAL_FROM = time(9, 8)  # order entry closes at random between 09:07 and 09:08; the result is from 09:08
PREOPEN_CANDLE, SESSION_OPEN = time(9, 9), time(9, 15)  # step 0b: the 09:09 candle's close is NSE's official open
FLAT_READ_FROM = time(9, 10)  # A22d: the pre-open result is final from the 09:08 or 09:09 candle (step 0b)
BASIS_0909, BASIS_FLAT = "candle_0909", "flat_0915"  # where an index's pre-open value came from (amendment 2)
VOLUME_AT = 5  # Groww's row: start, open, high, low, close, volume[, open interest]


class BadAnswer(ValueError):
    """The answer is not in the layout this reader knows: nothing of it is used."""


@dataclass(frozen=True)
class Reading:
    complete: bool
    source_time: datetime | None
    values: dict[str, str] = field(default_factory=dict)
    detail: str = ""  # why it is not complete


def read_gift_nifty(data: bytes, seen_at: datetime) -> Reading:
    """NSE's GIFT Nifty block: fresh when NSE's time is on seen_at's day and at most 15 minutes before it."""
    block = _object(data).get("data")
    gift = block.get("giftNifty") if isinstance(block, dict) else None
    if not isinstance(gift, dict):
        raise BadAnswer("no giftNifty block")
    try:
        nse_time = datetime.strptime(gift["timestmp"], GIFT_TIME).replace(tzinfo=IST)
        values = {"gift_level": str(float(gift["lastprice"])), "gift_contracts": str(int(gift["contractstraded"])),
                  "gift_expiry": str(gift["expirydate"])}  # fmt: skip
    except (KeyError, TypeError, ValueError) as exc:
        raise BadAnswer(f"giftNifty: {type(exc).__name__}") from exc
    age = seen_at - nse_time
    if nse_time.date() != seen_at.astimezone(IST).date() or age > GIFT_FRESH_FOR or age < -GIFT_AHEAD_ALLOWED:
        return Reading(False, nse_time, values, f"stale: NSE's time {nse_time:%d %b %H:%M}")
    return Reading(True, nse_time, values)


def read_preopen_list(data: bytes, day: date) -> Reading:
    """NSE's F&O pre-open list: complete when its time is the day's, from 09:08, with at least one stock."""
    answer = _object(data)
    if not isinstance(answer.get("data"), list):
        raise BadAnswer("no data list")
    if not answer["data"]:
        return Reading(False, None, {}, "empty list")
    try:
        nse_time = datetime.strptime(answer["timestamp"], PREOPEN_TIME).replace(tzinfo=IST)
        ieps = [item["metadata"]["iep"] for item in answer["data"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise BadAnswer(f"pre-open list: {type(exc).__name__}") from exc
    values = {"fo_stocks": str(len(ieps)), "fo_with_iep": str(sum(_positive(iep) for iep in ieps))}
    if nse_time.date() != day or nse_time.time() < PREOPEN_FINAL_FROM:
        return Reading(False, nse_time, values, f"not final: NSE's time {nse_time:%d %b %H:%M:%S}")
    return Reading(True, nse_time, values)


def read_index_preopen(data: bytes, day: date, prefix: str, seen_at: datetime) -> Reading:
    """The close of the day's 09:09 one-minute candle (Groww's answer as A16b's source keeps it); without it, read live
    from 09:10 to before 09:15, the close of Groww's lone flat 09:15 placeholder candle (A22d, amendment 2)."""
    rows = _object(data).get("candles")
    if not isinstance(rows, list):
        raise BadAnswer("no candle list")
    try:
        todays = [(c, row) for c, row in zip(parse_candles(rows), rows, strict=True) if c.start.date() == day]
    except CandleParse as exc:
        raise BadAnswer(f"candle row: {exc}") from exc
    candles = [c for c, _ in todays]
    at = datetime.combine(day, PREOPEN_CANDLE, IST)
    found = [c for c in candles if c.start == at]
    if found:
        return Reading(True, at + timedelta(minutes=1), _values(prefix, found[0].close, BASIS_0909))
    if _is_placeholder(todays, day, seen_at):
        return Reading(True, None, _values(prefix, candles[0].close, BASIS_FLAT))  # its 09:15 stamp is not its time
    if candles and all(c.start.time() >= SESSION_OPEN for c in candles):
        return Reading(False, None, {}, "no pre-open value: candles only from 09:15")
    return Reading(False, None, {}, "no 09:09 candle yet")


def _is_placeholder(todays: list[tuple[Candle, list]], day: date, seen_at: datetime) -> bool:
    """Live before 09:15 Groww serves one flat 09:15 candle with no volume, holding the pre-open price (23 Oct: equal to
    NSE's official open for both indices). From 09:15 the same shape may be a traded minute, so it is never taken."""
    if len(todays) != 1:
        return False
    candle, row = todays[0]
    seen = seen_at.astimezone(IST)
    flat = candle.open == candle.high == candle.low == candle.close
    volume = row[VOLUME_AT] if len(row) > VOLUME_AT else None
    return (candle.start == datetime.combine(day, SESSION_OPEN, IST) and flat and _no_volume(volume)
            and seen.date() == day and FLAT_READ_FROM <= seen.time() < SESSION_OPEN)  # fmt: skip


def _no_volume(volume) -> bool:
    return volume is None or (isinstance(volume, int | float) and not isinstance(volume, bool) and volume == 0)


def _values(prefix: str, close: float, basis: str) -> dict[str, str]:
    return {f"{prefix}_preopen": str(close), f"{prefix}_preopen_basis": basis}


def _object(data: bytes) -> dict:
    try:
        answer = json.loads(data)
    except ValueError as exc:  # also UnicodeDecodeError
        raise BadAnswer("not JSON") from exc
    if not isinstance(answer, dict):
        raise BadAnswer("not a JSON object")
    return answer


def _positive(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and value > 0
