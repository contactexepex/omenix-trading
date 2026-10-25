"""Core data structures shared by providers, analytics and strategies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
EXPIRY_CLOSE = time(15, 30)


def wall_clock() -> datetime:
    """The real time, whatever clock is installed (a replay clock is built on it)."""
    return datetime.now(UTC)


_clock: Callable[[], datetime] = wall_clock  # the process's one clock (story REH1: a rehearsal installs its own)


def install_clock(clock: Callable[[], datetime]) -> None:
    """Every clock read of the package goes through here (a test forbids `datetime.now` elsewhere); a rehearsal's
    replay clock is installed once, at process start, by its composition root."""
    global _clock
    _clock = clock


def now_ist() -> datetime:
    return _clock().astimezone(IST)


def now_utc() -> datetime:
    return _clock().astimezone(UTC)


def today_local() -> date:
    """The container's local date, as `date.today()` gave it (kept for the commands whose default was that)."""
    return _clock().astimezone().date()


@dataclass
class OptionQuote:
    strike: float
    kind: str  # "CE" or "PE"
    ltp: float
    bid: float | None = None
    ask: float | None = None
    oi: float = 0.0
    oi_change: float | None = None
    volume: float = 0.0
    iv: float | None = None  # percent, e.g. 12.5
    symbol: str | None = None

    @property
    def has_book(self) -> bool:
        return bool(self.bid and self.ask and self.bid > 0 and self.ask >= self.bid)

    @property
    def mid(self) -> float:
        if self.has_book:
            return (self.bid + self.ask) / 2
        return self.ltp


@dataclass(frozen=True)
class QuoteBook:
    """One contract's order book as the provider reported it (never filled in or guessed)."""

    symbol: str
    bid: float | None
    ask: float | None
    bid_qty: float | None
    ask_qty: float | None
    last: float | None
    last_trade_time: datetime | None
    book_source: str  # "fields" (best bid/offer fields) or "depth" (top of the market depth) or "" (none)
    raw_sha256: str  # SHA-256 of the provider's raw response, for audit
    quote_time: datetime | None = None  # when the provider says the quote was taken (NSE: its page timestamp)
    traded_today: bool | None = None  # NSE: the contract's day volume > 0 (it gives no last trade time)


@dataclass
class OptionChain:
    underlying: str
    spot: float
    expiry: date
    timestamp: datetime
    lot_size: int
    quotes: dict[tuple[float, str], OptionQuote] = field(default_factory=dict)
    source: str = ""

    def strikes(self) -> list[float]:
        return sorted({k for k, _ in self.quotes})

    def get(self, strike: float, kind: str) -> OptionQuote | None:
        return self.quotes.get((float(strike), kind))

    def atm_strike(self) -> float:
        return min(self.strikes(), key=lambda k: abs(k - self.spot))

    def strike_step(self) -> float:
        """Typical strike spacing near the money."""
        near = [k for k in self.strikes() if abs(k - self.spot) <= self.spot * 0.05]
        diffs = sorted(b - a for a, b in zip(near, near[1:]) if b > a)
        return diffs[len(diffs) // 2] if diffs else 50.0

    def years_to_expiry(self, at: datetime | None = None) -> float:
        at = at or self.timestamp
        if at.tzinfo is None:
            at = at.replace(tzinfo=IST)
        expiry_dt = datetime.combine(self.expiry, EXPIRY_CLOSE, tzinfo=IST)
        seconds = max((expiry_dt - at).total_seconds(), 3600.0)
        return seconds / (365.0 * 24 * 3600)

    def days_to_expiry(self, today: date | None = None) -> int:
        today = today or self.timestamp.date()
        return (self.expiry - today).days
