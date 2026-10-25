"""One quote of an index future (story G10 completion, criterion 3a; G7b's ask: V5 prices the future at mid under the
5% spread rule). Behind an interface: the `Provider` interface quotes option legs only, and NSE's level read gives a
future's last price and day volume but no bid or ask. Groww's adapter asks the same quote endpoint A16 asks for the near
future, in the read-only F&O segment. Research only: a quote, never an order."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..intraday.groww_source import FUTURE_SYMBOL
from ..models import QuoteBook
from ..providers.groww import GrowwProvider, _payload, parse_groww_quote_book

NO_SOURCE = "no future quote source for provider {name}"


class FutureQuotes(ABC):
    @abstractmethod
    def quote(self, expiry: date) -> QuoteBook:
        """NIFTY's future of `expiry`: bid, ask, last and last trade time as the provider gives them; raises on any
        failure (the caller records it, never a guessed price)."""


class GrowwFutureQuotes(FutureQuotes):
    def __init__(self, provider: GrowwProvider):
        self.provider = provider

    def quote(self, expiry: date) -> QuoteBook:
        symbol = FUTURE_SYMBOL.format(expiry=expiry, month=f"{expiry:%b}".upper())
        api = self.provider.api
        return parse_groww_quote_book(
            symbol, _payload(api.get_quote(trading_symbol=symbol, exchange=api.EXCHANGE_NSE, segment=api.SEGMENT_FNO))
        )


class NoFutureQuotes(FutureQuotes):
    """A provider with no future quote (NSE's public chain): every ask fails, named."""

    def __init__(self, name: str):
        self.name = name

    def quote(self, expiry: date) -> QuoteBook:
        raise RuntimeError(NO_SOURCE.format(name=self.name))
