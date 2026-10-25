"""The times a named capture adds to its sidecar (story A4e; G10's pack needs every field's own times, protocol v4
section 1.6): each chain call's request and receive time (spot comes from it), the level reads' (India VIX and the
futures, one call), and A16's clock check before the first and after the last request. No market request (expiries,
chain or levels) starts after the window's end; the quote books stop there too (A4c's `Slot.stop_requests_at`). The
default capture has no log, so its sidecar stays A4's byte for byte."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time

from ..intraday.clock import CLOCK_OK, CLOCK_PARTIAL, CLOCK_SKEW, CLOCK_UNCHECKED, ClockCheck
from ..models import IST, OptionChain
from ..providers.base import Provider
from .book_fetch import WINDOW_ENDED, WindowEnded
from .market_levels import LevelSource, MarketLevels

SEVERITY = (CLOCK_OK, CLOCK_PARTIAL, CLOCK_SKEW, CLOCK_UNCHECKED)


class CaptureLog:
    """One attempt's times: `begin` before its first request, `finish` after its last (it returns the sidecar keys)."""

    def __init__(self, clock: ClockCheck, now: Callable[[], datetime], stop: time):
        self.clock, self.now, self.stop = clock, now, stop
        self.chains: list[dict] = []
        self.levels: dict = {}
        self.statuses: list[str] = []
        self.skews: list[float] = []

    def begin(self) -> None:
        self.chains, self.levels, self.statuses, self.skews = [], {}, [], []
        self._read()

    def request_allowed(self) -> datetime:
        """The request's send time; WindowEnded after the window's end (a request at the end itself is allowed)."""
        sent = self.now()
        if sent > datetime.combine(sent.date(), self.stop, IST):
            raise WindowEnded(WINDOW_ENDED)
        return sent

    def chain(self, chain: OptionChain, sent: datetime, received: datetime) -> None:
        times = {"request_sent_at": sent.isoformat(), "response_received_at": received.isoformat()}
        self.chains.append({"expiry": chain.expiry.isoformat(), "spot": chain.spot, **times})

    def level_reads(self, sent: datetime, received: datetime) -> None:
        self.levels = {"levels_requested_at": sent.isoformat(), "levels_received_at": received.isoformat()}

    def finish(self) -> dict:
        self._read()
        return {
            "chains": self.chains, **self.levels, "clock_checks": self.statuses,
            "clock_status": max(self.statuses, key=SEVERITY.index),
            "clock_worst_skew_seconds": max(self.skews) if self.skews else None,
        }  # fmt: skip

    def _read(self) -> None:
        """A check that fails keeps its place as `clock_unchecked` (so before and after stay in order and the status
        cannot be clock_ok); it never stops the capture."""
        try:
            reading = self.clock.check()
        except Exception:
            self.statuses.append(CLOCK_UNCHECKED)
            return
        self.statuses.append(reading.status)
        if reading.worst is not None:
            self.skews.append(reading.worst)


class TimedProvider(Provider):
    """The capture's provider, unchanged, with each chain call's request and receive time written to the log and no
    expiries or chain request after the window's end."""

    def __init__(self, inner: Provider, log: CaptureLog):
        super().__init__({})  # lot sizes are never asked of the 3 pm recorder's provider
        self.inner, self.log = inner, log

    @property
    def name(self) -> str:
        return self.inner.name

    def expiries(self, underlying: str) -> list[date]:
        self.log.request_allowed()
        return self.inner.expiries(underlying)

    def chain(self, underlying: str, expiry: date) -> OptionChain:
        sent = self.log.request_allowed()
        chain = self.inner.chain(underlying, expiry)
        self.log.chain(chain, sent, self.log.now())
        return chain

    def quote_book(self, chain, strike, kind):
        return self.inner.quote_book(chain, strike, kind)  # stopped at the window's end by the slot (A4c)


class TimedLevels(LevelSource):
    """The level source, unchanged, with the request and receive time of its one call (both NSE answers had arrived
    by the return, so the receive time is an honest upper bound for India VIX and for the futures). After the window's
    end nothing is asked: the failure is recorded, never raised (LevelSource's rule)."""

    def __init__(self, inner: LevelSource, log: CaptureLog):
        self.inner, self.log, self.name = inner, log, inner.name

    def levels(self, underlying: str) -> MarketLevels:
        try:
            sent = self.log.request_allowed()
        except WindowEnded:
            return MarketLevels(failures=(f"levels: {WINDOW_ENDED}",))
        levels = self.inner.levels(underlying)
        self.log.level_reads(sent, self.log.now())
        return levels
