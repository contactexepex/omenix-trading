"""Funds and risk at the fill (story E8 rule 6; ChatGPT review 122 point 5; judge 203 conditions 1, 3 and 4).

Approved cash, available cash and margin can each change between the decision and the fill: other fills that morning,
an overnight margin change. So before an entry is written, C2's own rules run again on the due mark's copy and the
verdict account as it stands after the earlier fills (they are written first, oldest first), and C4's own maximum loss
is recomputed on the fill prices. It is a check, never a decision: its result is fill or miss, and no decision record
is written that E6, S1 or S2 could count (condition 1).

Every value the check reads must be valid in the same copy, or the entry is "missed, no quote" (condition 3): the
spot, a future of each expiry the market needs ("missed, no future for that expiry" when that alone is missing), and
every contract the proposal and the open trades hold. Other strikes may be missing. These are the paper desk's own
checks on its own accounts, never Groww's funds or margins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping

from ...books.book1_market import market_from_snapshot
from ...checks.validity_money import ProposedLeg, max_loss
from ...research_data.quote_snapshots import CutoffSnapshot, LiveQuote
from ...research_engine.implied_vol import ImpliedVolModel
from ...risk.inputs import Market, RiskBook
from ...risk.manager import RiskManager
from ..entries import EntryOrder
from .due_fill import PricedEntry
from .mark_levels import MarkSnapshot
from .outcomes import MISSED_FUNDS, MISSED_NO_FUTURE, MISSED_NO_QUOTE, MISSED_RISK_CAP

FUNDS_RULES = ("margin_room",)  # C2's funds rule (cash and stressed margin at entry); every other rule is a cap

BookLoader = Callable[[str, Market], RiskBook]  # an account and the fill-day market -> C2's view of that account


class FillRisk(ABC):
    @abstractmethod
    def miss(self, order: EntryOrder, priced: PricedEntry) -> str:
        """Why the entry may not fill at its due mark, or empty when it may."""


def fill_market(mark: MarkSnapshot, rate: float, model: ImpliedVolModel) -> Market | None:
    """C2's market at the due mark, from that copy only (Book 1's own builder); None without a usable spot."""
    prices = mark.prices
    if mark.spot is None:
        return None
    quotes = tuple(
        LiveQuote(q.expiry, q.strike, q.kind, q.bid, q.ask, not q.a4_problem, q.contract_id)
        for q in prices.quotes.values()
    )
    levels = CutoffSnapshot(prices.day, prices.finished_at, mark.spot, None, quotes, mark.futures)
    return market_from_snapshot(prices.day, levels, rate, model)


class FillDayRisk(FillRisk):
    def __init__(self, manager: RiskManager, books: BookLoader, rate: float, model: ImpliedVolModel,
                 max_loss_rs: float, charges: Mapping[str, float]):  # fmt: skip
        self.manager, self.books, self.rate, self.model = manager, books, rate, model
        self.max_loss_rs, self.charges = max_loss_rs, dict(charges)

    def miss(self, order: EntryOrder, priced: PricedEntry) -> str:
        market = fill_market(priced.mark, self.rate, self.model)
        if market is None:
            return MISSED_NO_QUOTE
        book = self.books(order.book, market)
        held = {contract for trade in book.open_trades for contract, units in trade.units.items() if units}
        needed = held | {leg.contract for leg in order.proposal.legs}
        missing = [contract for contract in needed if contract not in market.quotes]
        if missing:
            return _missing_reason(missing, priced.mark)
        decision = self.manager.evaluate(order.proposal, book, market)  # a check: never recorded
        failed = [v.rule for v in decision.verdicts if not v.ok]
        if any(rule in FUNDS_RULES for rule in failed):
            return MISSED_FUNDS
        if failed or self._loss_at_fill(priced) > self.max_loss_rs:
            return MISSED_RISK_CAP
        return ""

    def _loss_at_fill(self, priced: PricedEntry) -> float:
        """C4's own maximum loss (pads and charges included), on the prices this entry would fill at."""
        legs = [ProposedLeg(q.leg.leg.strike, q.leg.leg.kind, q.leg.leg.side, q.price) for q in priced.quotes]
        return max_loss(legs, priced.quotes[0].units, self.charges).total


def _missing_reason(missing: list[str], mark: MarkSnapshot) -> str:
    """A contract quoted in the copy whose expiry has no valid future there could not be priced for that reason alone
    (judge C's note: A16 records only the near-month future); any other gap is a missing quote."""
    futures = {f.expiry for f in mark.futures}
    expiries = {q.contract_id: q.expiry for q in mark.prices.quotes.values()}
    if all(contract in expiries and expiries[contract] not in futures for contract in missing):
        return MISSED_NO_FUTURE
    return MISSED_NO_QUOTE
