"""Reading one month's India VIX file into daily rows, refusing anything that is not a whole, clean month (A15).

A file is refused (ValueError naming why) when it is not NSE's JSON, holds no rows, holds as many rows as NSE's cap
(it may have been cut), names another index, has a day outside its month or twice, or a level that is not a number.
Values are copied as NSE gives them, never rounded or corrected: a level of 0 (NSE's open on 12 Feb and 30 Mar 2021)
or a day whose high and low do not contain its open and close is kept as published, and the checks list it
(`checks.py`).
"""

from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from .source import month_end

NSE_ROW_CAP = 70  # NSE's answer holds at most this many rows and silently drops the rest
NSE_INDEX_NAME = "INDIA VIX"
NSE_DATE_FORMAT = "%d-%b-%Y"  # 19-JUL-2010
NSE_FIELDS = {
    "open": "EOD_OPEN_INDEX_VAL",
    "high": "EOD_HIGH_INDEX_VAL",
    "low": "EOD_LOW_INDEX_VAL",
    "close": "EOD_CLOSE_INDEX_VAL",
}


@dataclass(frozen=True)
class VixDay:
    day: date
    open: float
    high: float
    low: float
    close: float


class VixMonthReader(ABC):
    """A publisher's month file format: its bytes to one row per day, or ValueError naming the problem."""

    @abstractmethod
    def read(self, data: bytes, month: date) -> list[VixDay]: ...


class NseVixJsonReader(VixMonthReader):
    def read(self, data: bytes, month: date) -> list[VixDay]:
        rows = _rows(data)
        if not rows:
            raise ValueError("NSE's answer holds no rows")
        if len(rows) >= NSE_ROW_CAP:
            raise ValueError(f"{len(rows)} rows: NSE's cap is {NSE_ROW_CAP}, so the answer may have been cut")
        days = [_day(row, month) for row in rows]
        seen = [d.day for d in days]
        twice = sorted({d for d in seen if seen.count(d) > 1})
        if twice:
            raise ValueError(f"days given twice: {', '.join(map(str, twice))}")
        return sorted(days, key=lambda d: d.day)


def _rows(data: bytes) -> list:
    try:
        document = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"not NSE's JSON answer ({exc.__class__.__name__}; an HTML error page?)") from exc
    rows = document.get("data") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ValueError('not NSE\'s JSON answer: no "data" list')
    return rows


def _day(row, month: date) -> VixDay:
    if not isinstance(row, dict) or row.get("EOD_INDEX_NAME") != NSE_INDEX_NAME:
        raise ValueError(f"a row that is not {NSE_INDEX_NAME}: {row!r:.120}")
    try:
        day = datetime.strptime(str(row.get("EOD_TIMESTAMP")), NSE_DATE_FORMAT).date()
    except ValueError as exc:
        raise ValueError(f"bad date {row.get('EOD_TIMESTAMP')!r}") from exc
    if not month <= day <= month_end(month):
        raise ValueError(f"{day} is outside the month {month:%Y-%m}")
    return VixDay(day, **{name: _level(row, key, day) for name, key in NSE_FIELDS.items()})


def _level(row: dict, key: str, day: date) -> float:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{day}: {key} is {value!r}, not a number")
    return float(value)
