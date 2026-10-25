"""One day's option chain as G13 reads it (section 1), whatever its source: each expiry's quotes and same-expiry
future, and the quote filter that decides which prices the record uses. Sources sit behind `ChainSource`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from datetime import date

from .constants import EOD_MIN_PRICE_RS, SPREAD_FLOOR_RS, SPREAD_SHARE

INVALID, ONE_SIDED, WIDE = "invalid", "one_sided", "wide"
NO_TRADE, BELOW_MIN_PRICE = "no_trade", "below_min_price"


@dataclass(frozen=True)
class Quote:
    strike: float
    kind: str  # "CE" or "PE"
    price: float | None  # the mid of a two-sided quote, or an end-of-day traded close
    bid: float | None = None
    ask: float | None = None
    valid: bool = True
    volume: int | None = None  # end-of-day only
    contract_id: str = ""


@dataclass(frozen=True)
class ExpiryChain:
    expiry: date
    quotes: tuple[Quote, ...]
    future: float | None  # the same-expiry future's last trade (3 pm) or close (end of day)


@dataclass(frozen=True)
class ChainDay:
    underlying: str
    day: date
    source: str  # groww, nse or panel
    snapshot_id: str
    inputs_sha256: str  # the snapshot CSV's SHA-256 (or the panel rows' digest)
    observed_at: str  # ISO time the capture finished (3 pm) or the session's close (panel)
    spot: float | None
    expiries: tuple[ExpiryChain, ...]
    source_note: str = ""  # why an earlier source was passed over (a read failure), if one was


class ChainSource(ABC):
    @abstractmethod
    def chain(self, underlying: str, day: date) -> ChainDay | None:
        """The day's chain, or None when none was captured."""


class QuoteFilter(ABC):
    @abstractmethod
    def reason(self, quote: Quote) -> str | None:
        """Why a quote is not used; None when it is."""


class SpreadFilter(QuoteFilter):
    """3 pm quotes: valid, two-sided, and `ask - bid <= max(10% of mid, Rs 0.50)` (reasoning only)."""

    def reason(self, quote: Quote) -> str | None:
        if not quote.valid:
            return INVALID
        if quote.price is None or quote.bid is None or quote.ask is None:
            return ONE_SIDED
        return WIDE if quote.ask - quote.bid > max(SPREAD_SHARE * quote.price, SPREAD_FLOOR_RS) else None


class TradedCloseFilter(QuoteFilter):
    """End-of-day closes: traded that day and at least Rs 0.50."""

    def reason(self, quote: Quote) -> str | None:
        if not quote.volume or quote.volume <= 0 or quote.price is None:
            return NO_TRADE
        return BELOW_MIN_PRICE if quote.price < EOD_MIN_PRICE_RS else None


@dataclass(frozen=True)
class UsedQuotes:
    quotes: tuple[Quote, ...]
    dropped: dict[str, int]  # reason -> count

    def mid(self, strike: float, kind: str) -> float | None:
        return next((q.price for q in self.quotes if q.strike == strike and q.kind == kind), None)

    def pairs(self) -> list[tuple[float, float, float]]:
        """`(strike, call, put)` for every strike with both sides used."""
        calls = {q.strike: q.price for q in self.quotes if q.kind == "CE"}
        puts = {q.strike: q.price for q in self.quotes if q.kind == "PE"}
        return [(k, calls[k], puts[k]) for k in sorted(calls.keys() & puts.keys())]


def used_quotes(chain: ExpiryChain, rule: QuoteFilter) -> UsedQuotes:
    reasons = [(q, rule.reason(q)) for q in chain.quotes]
    dropped = Counter(r for _, r in reasons if r is not None)
    return UsedQuotes(tuple(q for q, r in reasons if r is None), dict(sorted(dropped.items())))
