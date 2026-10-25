"""What the risk manager checks (story C2): a proposed trade, one book's own account and positions, and the market.

Every input names its contracts by the exchange's symbol, as the paper account (E1) records them; the market snapshot
gives each contract's strike, type, expiry, mid and implied volatility. A missing quote, a stale quote for a new
trade, or an open trade without its recorded terms is an input error, and the risk manager then refuses the trade
(fails closed): a price or a margin is never invented.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from ..books.equity import AccountState, Mark
from ..constants import OPTION_CALL, OPTION_PUT, STRUCTURES_BOUGHT_ONLY
from ..research_data.panel_reader import FutureQuote
from ..research_engine.structures import Leg


class RiskInputError(ValueError):
    """An input the risk manager cannot check a trade with; the trade is refused."""


@dataclass(frozen=True)
class ContractQuote:
    strike: float
    kind: str  # "CE" or "PE"
    expiry: date
    mid: float  # mid of valid quotes, or the last valid mark when `stale`
    iv: float  # implied volatility as a fraction, from the same mid, by the engine's model (B1's Black-76)
    stale: bool = False

    def __post_init__(self):
        if self.kind not in (OPTION_CALL, OPTION_PUT):
            raise RiskInputError(f"option type must be CE or PE, not {self.kind!r}")
        values = (self.strike, self.mid, self.iv)
        if not all(math.isfinite(v) for v in values) or self.strike <= 0 or self.mid < 0 or self.iv <= 0:
            raise RiskInputError(f"unusable quote: strike {self.strike}, mid {self.mid}, iv {self.iv}")


@dataclass(frozen=True)
class Market:
    day: date  # the decision day; one calendar day passes in each stress scenario
    spot: float  # NIFTY
    rate: float  # risk-free rate (config.yaml `risk_free_rate`): only discounts under Black-76
    quotes: Mapping[str, ContractQuote]
    futures: Mapping[date, FutureQuote]  # NIFTY future by expiry: the forward each option is priced on (Black-76)

    def quote(self, contract: str) -> ContractQuote:
        if contract not in self.quotes:
            raise RiskInputError(f"no quote for {contract}")
        quote = self.quotes[contract]
        if quote.expiry < self.day:
            raise RiskInputError(f"{contract} expired on {quote.expiry}, before {self.day}")
        return quote

    def marks(self) -> dict[str, Mark]:
        """The marks the paper account (E1) values open positions with."""
        return {contract: Mark(q.mid, q.stale) for contract, q in self.quotes.items()}


@dataclass(frozen=True)
class TradeTerms:
    """What a margin row is looked up by: the structure's code (SF, SC, BF or a STR1 code), width in points out of the
    money and number of lots. Width 0 (the ATM strike) is only for a bought-only structure (LC, LP)."""

    structure: str
    width: float
    lots: int

    def __post_init__(self):
        if self.lots <= 0 or self.width < 0 or (self.width == 0 and not self.bought_only):
            raise RiskInputError(f"lots and width must be positive (width 0 only for LC and LP): {self}")

    @property
    def bought_only(self) -> bool:
        """No sold leg: NSE blocks no margin for it (the premium is paid in full at entry)."""
        return self.structure in STRUCTURES_BOUGHT_ONLY


@dataclass(frozen=True)
class ProposedLeg:
    contract: str
    leg: Leg  # strike, type and side (bought +1, sold -1) of one unit


@dataclass(frozen=True)
class Proposal:
    trade_id: str
    terms: TradeTerms
    lot_size: int  # units per lot (config.yaml `lot_sizes`)
    legs: tuple[ProposedLeg, ...]

    def __post_init__(self):
        if self.lot_size <= 0 or not self.legs:
            raise RiskInputError(f"proposal {self.trade_id}: needs legs and a positive lot size")
        contracts = [p.contract for p in self.legs]
        if len(set(contracts)) != len(contracts):
            raise RiskInputError(f"proposal {self.trade_id}: a contract appears twice")

    @property
    def units(self) -> int:
        """Units per leg: lots x lot size."""
        return self.terms.lots * self.lot_size

    def signed_units(self) -> dict[str, int]:
        return {p.contract: p.leg.side * self.units for p in self.legs}

    def entry_prices(self, market: Market) -> list[float]:
        """Each leg's quoted price today. A new trade is never priced on a stale mark or on a quote that does not
        match its leg."""
        prices = []
        for proposed in self.legs:
            quote = market.quote(proposed.contract)
            if quote.stale:
                raise RiskInputError(f"proposal {self.trade_id}: {proposed.contract} has only a stale mark")
            if (quote.strike, quote.kind) != (proposed.leg.strike, proposed.leg.kind):
                raise RiskInputError(f"proposal {self.trade_id}: {proposed.contract} is not {proposed.leg}")
            prices.append(quote.mid)
        return prices


@dataclass(frozen=True)
class OpenTrade:
    trade_id: str
    terms: TradeTerms
    units: Mapping[str, int]  # contract -> signed units still held (long +, short -)
    cash_flow: float  # premium received minus paid, minus charges, so far (E1)


@dataclass(frozen=True)
class SessionTrade:
    """A trade first filled on the decision day, open or already closed: its held units and cash flow after each fill
    time that day, in order. C5's new risk per session counts the largest maximum loss it carried (owner, 15 Oct
    2026, "3 A": a trade opened and closed in the same session still counts)."""

    trade_id: str
    states: tuple[tuple[Mapping[str, int], float], ...]


@dataclass(frozen=True)
class RiskBook:
    """One book's own account: nothing in it comes from another book (design 12.4)."""

    name: str
    state: AccountState  # E1, marked with today's marks
    open_trades: tuple[OpenTrade, ...]
    closed_equity: tuple[tuple[date, float], ...]  # (day, closed equity at that day's close): start, then each change
    restarts: tuple[date, ...]  # days of the owner's brake restarts, oldest first
    session_trades: tuple[SessionTrade, ...] | None = None  # None: not known (an old record), so new risk is refused
