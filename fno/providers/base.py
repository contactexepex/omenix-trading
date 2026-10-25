"""Market-data provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..models import OptionChain, QuoteBook

INDEX_NAMES = {
    "NIFTY": "NIFTY 50",
    "BANKNIFTY": "NIFTY BANK",
    "FINNIFTY": "NIFTY FINANCIAL SERVICES",
    "MIDCPNIFTY": "NIFTY MID SELECT",
}


def is_index(underlying: str) -> bool:
    return underlying.upper() in INDEX_NAMES


class Provider(ABC):
    name = "base"

    def __init__(self, config: dict):
        self.config = config

    def fallback_lot_size(self, underlying: str) -> int:
        return int(self.config.get("lot_sizes", {}).get(underlying.upper(), 1))

    @abstractmethod
    def expiries(self, underlying: str) -> list[date]:
        """Upcoming expiry dates, soonest first."""

    @abstractmethod
    def chain(self, underlying: str, expiry: date) -> OptionChain:
        """Full option chain for one expiry."""

    def quote_book(self, chain: OptionChain, strike: float, kind: str) -> QuoteBook | None:
        """The contract's full order book (bid, ask, sizes, last trade time) for the 3 pm quote recorder. None when the
        provider cannot give one; the recorder then records the contract as unquoted."""
        return None
