"""Groww's NIFTY 50 index candles for the back-fill (story A16b), behind `IntradayCandleSource`: 15-minute candles for
a window of up to 90 days, and one session's 1-minute candles for the check. Read-only: the adapter holds only
A16's `ReadOnlyGroww`. Calls are paced (one at a time, at least `MIN_GAP_SECONDS` between starts: at most 2 a second,
under the 4-5 a second A16 measured as safe). Any failure of a call, or an answer without a candle list, is
`CandleCallFailed` (transient: named by class only, never by an exception's text, which could carry a credential)."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from .index_reading import CANDLE_SYMBOL

MIN_GAP_SECONDS = 0.5
FIFTEEN_MINUTES, ONE_MINUTE = "15m", "1m"
DAY_FROM, DAY_TO = "09:00:00", "15:59:59"
CALL_TIMEOUT_SECONDS = 30
INTERVALS = {FIFTEEN_MINUTES: "CANDLE_INTERVAL_MIN_15", ONE_MINUTE: "CANDLE_INTERVAL_MIN_1"}  # SDK constant names


class CandleCallFailed(RuntimeError):
    """The call failed or its answer was unreadable: transient, tried again on the next run."""


@dataclass(frozen=True)
class CandleAnswer:
    kind: str  # FIFTEEN_MINUTES or ONE_MINUTE
    start: date
    end: date
    raw: bytes  # the answer as received, serialised with sorted keys
    rows: list  # Groww's candle rows
    requested_at: datetime
    received_at: datetime


class IntradayCandleSource(ABC):
    @abstractmethod
    def candles(self, start: date, end: date) -> CandleAnswer:
        """15-minute candles of every day from start to end (at most 90 days)."""

    @abstractmethod
    def minute_candles(self, day: date) -> CandleAnswer:
        """One day's 1-minute candles, 09:00-15:59."""


class GrowwCandleSource(IntradayCandleSource):
    def __init__(self, api, clock: Callable[[], datetime], sleep=time.sleep, monotonic=time.monotonic,
                 symbol: str = CANDLE_SYMBOL):  # fmt: skip
        """`api`: A16's `ReadOnlyGroww`, never the SDK client itself; `symbol`: Groww's index (A22 adds BANKNIFTY)."""
        self.api, self.clock, self.sleep, self.monotonic, self.symbol = api, clock, sleep, monotonic, symbol
        self._last_start: float | None = None

    def candles(self, start: date, end: date) -> CandleAnswer:
        return self._call(FIFTEEN_MINUTES, start, end, INTERVALS[FIFTEEN_MINUTES])

    def minute_candles(self, day: date) -> CandleAnswer:
        return self._call(ONE_MINUTE, day, day, INTERVALS[ONE_MINUTE])

    def _call(self, kind: str, start: date, end: date, interval: str) -> CandleAnswer:
        """Every SDK touch inside the try: reading a constant signs in to Groww, whose error text may hold a key."""
        self._pace()
        requested = self.clock()
        try:
            answer = self.api.get_historical_candles(
                exchange=self.api.EXCHANGE_NSE, segment=self.api.SEGMENT_CASH, groww_symbol=self.symbol,
                start_time=f"{start} {DAY_FROM}", end_time=f"{end} {DAY_TO}",
                candle_interval=getattr(self.api, interval), timeout=CALL_TIMEOUT_SECONDS,
            )  # fmt: skip
            rows = answer.get("candles") if isinstance(answer, dict) else None
            raw = json.dumps(answer, sort_keys=True, separators=(",", ":")).encode()
        except Exception as exc:  # the SDK raises its own and requests' errors; the class name only
            raise CandleCallFailed(f"Groww {kind} {start}..{end}: {type(exc).__name__}") from None
        if not isinstance(rows, list):  # Groww answers an empty list for a day without candles (probed)
            raise CandleCallFailed(f"Groww {kind} {start}..{end}: no candle list in the answer")
        return CandleAnswer(kind, start, end, raw, rows, requested, self.clock())

    def _pace(self) -> None:
        now = self.monotonic()
        if self._last_start is not None and now - self._last_start < MIN_GAP_SECONDS:
            self.sleep(MIN_GAP_SECONDS - (now - self._last_start))
        self._last_start = self.monotonic()
