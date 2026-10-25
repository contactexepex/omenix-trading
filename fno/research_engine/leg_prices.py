"""A leg's price on one day (story B2, protocol section 4): its close if it traded that day (volume > 0), else its
settlement price, flagged. Settlement is a valuation proxy, not an executable price.

A price that is missing or not above zero is no price (the leg is unfillable). That covers a 0.00 settlement: on its
expiry day NSE reports 0.00 there up to 30 Jan 2020 (research/data/nifty-panel/README.md). From 6 Feb 2020 the
expiry-day settlement is the Nifty 50 close instead, also not an option price, so an expiry day's settlement is never
used (cycles exit at least 21 days before expiry; this guards any other caller).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from ..constants import CycleStatus
from ..research_data.panel_reader import OptionQuote
from .structures import Contract


@dataclass(frozen=True)
class LegPrice:
    price: float | None  # None: no usable price
    on_settlement: bool  # the leg did not trade that day: the price is NSE's settlement price


MISSING = LegPrice(None, False)


def contracts_on(quotes: Sequence[OptionQuote]) -> dict[Contract, OptionQuote]:
    """One expiry's quotes of one day, by contract."""
    return {(q.strike, q.kind): q for q in quotes}


def leg_price(quote: OptionQuote | None, day: date) -> LegPrice:
    if quote is None:
        return MISSING
    if quote.volume > 0:
        return LegPrice(quote.close if quote.close > 0 else None, False)
    if day >= quote.expiry or quote.settle <= 0:
        return LegPrice(None, True)
    return LegPrice(quote.settle, True)


def fill_problem(prices: Sequence[LegPrice]) -> CycleStatus | None:
    """`unfillable` if any leg has no price or more than half the legs are on settlement prices; else None."""
    if any(p.price is None for p in prices) or 2 * sum(p.on_settlement for p in prices) > len(prices):
        return CycleStatus.UNFILLABLE
    return None
