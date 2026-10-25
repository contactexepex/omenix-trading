"""What a v4 pack holds (story G10 part 2, section 1). Every value carries its own `observed_at`: this host's checked
clock when the answer arrived (protocol 1.6), never an exchange's last-trade time, which is kept only for the "traded
today" check."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime


@dataclass(frozen=True)
class Level:
    """A single observed number: NIFTY spot."""

    value: float
    observed_at: datetime


@dataclass(frozen=True)
class VixLevel:
    value: float
    observed_at: datetime
    nse_time: datetime | None  # NSE's own time for the value, where NSE gives one


@dataclass(frozen=True)
class FutureQuote:
    """The future of expiry `e`, the nearest monthly expiry strictly after the day (protocol 1.5, V5's expiry). `last`
    and `volume` come from NSE's level read (`observed_at`); `bid`, `ask` and `last_trade_time` from the provider's own
    quote (`quoted_at`; all None when that quote failed). `last_trade_time` and `volume` serve the traded-today rule
    only (G7b's ask; A4's `traded_today`), never as a time of observation."""

    expiry: date
    last: float | None
    bid: float | None
    ask: float | None
    observed_at: datetime
    last_trade_time: datetime | None = None
    volume: int | None = None
    quoted_at: datetime | None = None


@dataclass(frozen=True)
class ChainQuote:
    expiry: date
    strike: float
    kind: str  # CE or PE
    bid: float | None
    ask: float | None
    last: float | None
    last_trade_time: datetime | None
    observed_at: datetime

    @property
    def mid(self) -> float | None:
        """(bid + ask) / 2 only when both sides are present."""
        return None if self.bid is None or self.ask is None else (self.bid + self.ask) / 2


@dataclass(frozen=True)
class Iv30:
    value: float  # annualised, in volatility points (G1's unit)
    flagged: bool  # a single-expiry estimate (protocol 1.6)
    expiries: tuple[date, ...]
    method: str  # the G1 estimator's name and file hash
    observed_by: datetime  # the latest observed_at of its inputs


@dataclass(frozen=True)
class Pack:
    day: date
    label: str  # A, the 14:30 capture (the only label a pack carries)
    source: str
    provider: str
    captured_from: str  # the capture this pack was built from
    released_at: datetime
    spot: Level
    future: FutureQuote
    india_vix: VixLevel
    chain: tuple[ChainQuote, ...]
    iv30: Iv30
    v4_expiry: date | None = None  # the expiry G7b's rule chose at the capture (None: none chosen), never recomputed

    def observed_by(self) -> datetime:
        """The latest `observed_at` of any field: the release record's `observed_by`."""
        times = [self.spot.observed_at, self.future.observed_at, self.india_vix.observed_at, self.iv30.observed_by]
        quoted = [self.future.quoted_at] if self.future.quoted_at else []
        return max(times + quoted + [quote.observed_at for quote in self.chain])


FIELD_NAMES = {
    kind: tuple(f.name for f in fields(kind)) for kind in (Level, VixLevel, FutureQuote, ChainQuote, Iv30, Pack)
}
