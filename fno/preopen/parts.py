"""The four parts of the morning capture (story A22), behind one port: each has its window and answers one read
(raw bytes, its `Reading`, our `seen_at`). A transport failure is `PartFailed`; an answer outside its layout is the
readers' `BadAnswer`. Adapters: NSE's GIFT Nifty and F&O pre-open list (JSON, through the shared polite session) and
Groww's 1-minute index candles through A16b's read-only `IntradayCandleSource`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import requests

from ..intraday.candle_source import CandleCallFailed, IntradayCandleSource
from .answers import Reading, read_gift_nifty, read_index_preopen, read_preopen_list

GIFT_URL = "https://www.nseindia.com/api/NextApi/apiClient?functionName=getGiftNifty"
FO_PREOPEN_URL = "https://www.nseindia.com/api/market-data-pre-open?key=FO"
TIMEOUT_SECONDS = 20
GIFT_WINDOW = (time(8, 40), time(8, 45))  # opens at, closes at (the last read is one second before it)
FO_WINDOW, INDEX_WINDOW = (time(9, 8, 30), time(9, 11)), (time(9, 10), time(9, 11))
LAST_READ_MARGIN = timedelta(seconds=1)  # a part's last read starts this long before its window's close
# A22e: the two index parts share their due times and Groww answers one paced call at a time (about 1-2 s each), so
# their last read starts 15 s before the close and the second is not received after it only for being read second
INDEX_LAST_READ_MARGIN = timedelta(seconds=15)


class PartFailed(RuntimeError):
    """The read did not reach an answer (network, HTTP status, Groww): named by kind, never by a value."""


@dataclass(frozen=True)
class Answer:
    raw: bytes
    reading: Reading
    seen_at: datetime


class PreopenPart(ABC):
    name: str
    window: tuple[time, time]
    last_read_margin: timedelta = LAST_READ_MARGIN

    @abstractmethod
    def answer(self, day: date) -> Answer:
        """One read now; PartFailed or BadAnswer when there is nothing to use."""

    @abstractmethod
    def read(self, data: bytes, day: date, seen_at: datetime) -> Reading:
        """The part's reader on one raw answer seen at `seen_at` (a rehearsal replays recorded bytes through it)."""


class NseJsonPart(PreopenPart):
    url: str

    def __init__(self, session: requests.Session, clock: Callable[[], datetime]):
        self.session, self.clock = session, clock

    def answer(self, day: date) -> Answer:
        try:
            response = self.session.get(self.url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise PartFailed(f"NSE: {type(exc).__name__}") from None
        seen_at = self.clock()
        if response.status_code != 200:
            raise PartFailed(f"NSE: HTTP {response.status_code}")
        return Answer(response.content, self.read(response.content, day, seen_at), seen_at)


class NseGiftNifty(NseJsonPart):
    name, window, url = "gift", GIFT_WINDOW, GIFT_URL

    def read(self, data: bytes, day: date, seen_at: datetime) -> Reading:
        return read_gift_nifty(data, seen_at)


class NsePreopenList(NseJsonPart):
    name, window, url = "fo_list", FO_WINDOW, FO_PREOPEN_URL

    def read(self, data: bytes, day: date, seen_at: datetime) -> Reading:
        return read_preopen_list(data, day)


class GrowwIndexPreopen(PreopenPart):
    window, last_read_margin = INDEX_WINDOW, INDEX_LAST_READ_MARGIN

    def __init__(self, name: str, source: IntradayCandleSource):
        """`name`: the index's day-row prefix (`nifty`, `banknifty`); `source`: its read-only candle source."""
        self.name, self.source = name, source

    def answer(self, day: date) -> Answer:
        try:
            candles = self.source.minute_candles(day)
        except CandleCallFailed as exc:
            raise PartFailed(str(exc)) from None
        return Answer(candles.raw, self.read(candles.raw, day, candles.received_at), candles.received_at)

    def read(self, data: bytes, day: date, seen_at: datetime) -> Reading:
        return read_index_preopen(data, day, self.name, seen_at)
