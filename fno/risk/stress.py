"""Whole-account stress tests with full repricing (story C2, design 8.1).

Every leg of the book's open trades and of the proposal is revalued with the project's implied-volatility model (B1's
`ImpliedVolModel`; the app uses `Black76`: the option priced on its same-expiry NIFTY future, the rate only
discounting), so the volatilities in the quotes and the repricing use one model and a zero-move, zero-day scenario
values every leg at its mark (judge 43: Black-Scholes on spot with Black-76 volatilities was off by about Rs 1,000 a lot
per ATM leg). Each leg is revalued with the underlying moved by the scenario's NIFTY move, its own current implied
volatility times the scenario's factor (plus any added points), after the scenario's calendar days of time decay; on
expiry a leg is worth its intrinsic value. Losses are summed across all legs and trades: no netting beyond the legs
themselves. Two losses are reported for every trade: from its current marked value and from its entry (its cash flow
so far). The loss the stress limit counts is each open trade's loss from its current mark plus the proposal's loss from
its entry, so the proposal's pads and charges count too.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..constants import OPTION_CALL
from ..research_engine.implied_vol import ImpliedVolModel, OptionPricing
from .inputs import ContractQuote, Market, Proposal, RiskBook, RiskInputError
from .settings import Scenario

DAYS_PER_YEAR = 365.0


@dataclass(frozen=True)
class Shock:
    name: str
    nifty_move_pct: float
    iv_factor: float = 1.0
    iv_add: float = 0.0  # volatility added after the factor, as a fraction (5 points = 0.05)
    days: int = 0

    @classmethod
    def of(cls, scenario: Scenario) -> Shock:
        return cls(scenario.name, scenario.nifty_move_pct, scenario.iv_factor, 0.0, scenario.days)


@dataclass(frozen=True)
class StressPosition:
    trade_id: str
    units: Mapping[str, int]  # contract -> signed units
    cash_flow: float  # premium received minus paid, minus charges (for the proposal: its estimated entry)
    proposed: bool = False  # True: the stress limit counts its loss from entry, not from a mark


@dataclass(frozen=True)
class TradeStress:
    trade_id: str
    loss_from_marks: float
    loss_from_entry: float
    proposed: bool

    @property
    def counted(self) -> float:
        return self.loss_from_entry if self.proposed else self.loss_from_marks


@dataclass(frozen=True)
class ShockResult:
    shock: Shock
    trades: tuple[TradeStress, ...]

    @property
    def counted_loss(self) -> float:
        """Combined loss: open trades from their current marks plus the proposal from its entry."""
        return sum(t.counted for t in self.trades)

    @property
    def loss_from_marks(self) -> float:
        return sum(t.loss_from_marks for t in self.trades)

    @property
    def loss_from_entry(self) -> float:
        return sum(t.loss_from_entry for t in self.trades)


def stress_positions(book: RiskBook, proposal: Proposal | None, proposal_cash_flow: float = 0.0) -> list:
    """The book's own open trades, plus the proposal when there is one: never another book's."""
    positions = [StressPosition(t.trade_id, t.units, t.cash_flow) for t in book.open_trades]
    if proposal is not None:
        positions.append(StressPosition(proposal.trade_id, proposal.signed_units(), proposal_cash_flow, proposed=True))
    return positions


def _intrinsic(quote: ContractQuote, underlying: float) -> float:
    gap = underlying - quote.strike if quote.kind == OPTION_CALL else quote.strike - underlying
    return max(gap, 0.0)


class StressEngine:
    def __init__(self, model: ImpliedVolModel):
        self.model = model  # the same model the quotes' implied volatilities come from

    def underlying(self, quote: ContractQuote, market: Market) -> float:
        underlying = self.model.underlying(market.spot, market.futures.get(quote.expiry))
        if underlying is None:
            raise RiskInputError(f"no usable NIFTY future for expiry {quote.expiry}: the option cannot be priced")
        return underlying

    def leg_value(self, contract: str, units: int, market: Market, shock: Shock) -> float:
        quote = market.quote(contract)
        underlying = self.underlying(quote, market) * (1 + shock.nifty_move_pct / 100)
        years = max((quote.expiry - market.day).days - shock.days, 0) / DAYS_PER_YEAR
        if years == 0:
            return units * _intrinsic(quote, underlying)
        sigma = quote.iv * shock.iv_factor + shock.iv_add
        return units * self.model.price(
            OptionPricing(quote.mid, underlying, quote.strike, quote.kind, years, market.rate), sigma
        )

    def marked_value(self, position: StressPosition, market: Market) -> float:
        return sum(units * market.quote(contract).mid for contract, units in position.units.items())

    def trade_stress(self, position: StressPosition, market: Market, shock: Shock) -> TradeStress:
        shocked = sum(self.leg_value(c, n, market, shock) for c, n in position.units.items())
        loss_from_marks = self.marked_value(position, market) - shocked
        loss_from_entry = -(position.cash_flow + shocked)
        return TradeStress(position.trade_id, loss_from_marks, loss_from_entry, position.proposed)

    def run(self, positions: Sequence[StressPosition], market: Market, shocks: Sequence[Shock]) -> list[ShockResult]:
        return [ShockResult(s, tuple(self.trade_stress(p, market, s) for p in positions)) for s in shocks]
