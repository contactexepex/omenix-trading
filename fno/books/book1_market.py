"""Book 1's market at the decision (story E5): the day's canonical A4 snapshot as C2 and D2 read it. Each contract with
a valid two-sided quote enters at its mid, named by the provider's recorded symbol (what the paper account and E4's
fills name it by), with its implied volatility by B1's Black-76 on the same-expiry future (the forward); the futures
come from the same capture. A quote without a mid, a symbol or an implied volatility is left out, never guessed (D2
then finds no candidate on it). No price here is ever a fill price: E4 fills at the execution capture."""

from __future__ import annotations

from datetime import date

from ..research_data.quote_snapshots import CutoffSnapshot
from ..research_engine.implied_vol import ImpliedVolModel, OptionPricing
from ..risk.inputs import ContractQuote, Market

DAYS_PER_YEAR = 365.0


class NoMarket(ValueError):
    """The day's snapshot cannot give a market (no spot): Book 1 decides nothing on it."""


def market_from_snapshot(day: date, snapshot: CutoffSnapshot, rate: float, model: ImpliedVolModel) -> Market:
    if not snapshot.spot:
        raise NoMarket(f"the canonical snapshot of {day} has no spot")
    futures = {f.expiry: f for f in snapshot.futures}
    quotes = {}
    for quote in snapshot.quotes:
        forward = model.underlying(snapshot.spot, futures.get(quote.expiry))
        if quote.mid is None or not quote.contract_id or forward is None:
            continue
        years = (quote.expiry - day).days / DAYS_PER_YEAR
        iv = model.implied_vol(OptionPricing(quote.mid, forward, quote.strike, quote.kind, years, rate))
        if iv is not None:
            quotes[quote.contract_id] = ContractQuote(quote.strike, quote.kind, quote.expiry, quote.mid, iv)
    return Market(day, snapshot.spot, rate, quotes, futures)
