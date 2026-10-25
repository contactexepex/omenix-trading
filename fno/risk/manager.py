"""The risk manager (story C2): every rule checks the proposal against the proposal's own book only.

A trade may open only when every rule passes. Every rule runs, so a refusal shows all its reasons. An unusable input
(a missing quote or margin, an open trade without terms, a malformed owner override) refuses the trade with the input's
problem as the reason: the check fails closed, never open. The decision record carries the stressed-margin method in
force and any stale marks, so the judge can reproduce it. It also carries the proposal it judged and that proposal's
entry cash at the modelled prices: the paper desk (E4) fills only that proposal, at an entry no worse than that cash.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .inputs import Market, Proposal, RiskBook
from .trade_costs import TradeCosts
from .verdict import RiskRule, RiskVerdict

INPUT_CHECK = "inputs"


@dataclass(frozen=True)
class RiskDecision:
    book: str
    trade_id: str
    day: str
    verdicts: tuple[RiskVerdict, ...]
    stressed_margin: Mapping[str, str]
    stale_marks: tuple[str, ...]
    entry_cash_rs: float | None = None  # the approved entry: premium at the modelled fills minus entry charges
    proposal: Proposal | None = None  # the proposal this decision judged

    @property
    def ok(self) -> bool:
        return all(v.ok for v in self.verdicts)

    @property
    def reasons(self) -> list[str]:
        return [f"{v.rule}: {v.reason}" for v in self.verdicts if not v.ok]

    def record(self) -> dict:
        return {
            "book": self.book,
            "trade_id": self.trade_id,
            "day": self.day,
            "ok": self.ok,
            "stressed_margin": dict(self.stressed_margin),
            "stale_marks": list(self.stale_marks),
            "entry_cash_rs": self.entry_cash_rs,
            "verdicts": [
                {"rule": v.rule, "ok": v.ok, "reason": v.reason, "numbers": dict(v.numbers)} for v in self.verdicts
            ],
        }


def _input_verdict(proposal: Proposal, book: RiskBook) -> RiskVerdict:
    if any(t.trade_id == proposal.trade_id for t in book.open_trades):
        return RiskVerdict(INPUT_CHECK, False, f"trade {proposal.trade_id} is already open in {book.name}")
    return RiskVerdict(INPUT_CHECK, True, "proposal is new to this book")


def _checked(rule: RiskRule, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
    try:
        return rule.check(proposal, book, market)
    except ValueError as problem:  # every input error (RiskInputError, MissingMark, a malformed row) fails closed
        return RiskVerdict(rule.name, False, f"refused, input not usable: {problem}")


def _entry_cash(costs: TradeCosts | None, proposal: Proposal, market: Market) -> float | None:
    """The proposal's entry cash at the modelled prices; None when it cannot be priced (the decision is refused)."""
    if costs is None:
        return None
    try:
        return costs.entry_cash_flow(proposal, market)
    except ValueError:
        return None


class RiskManager:
    def __init__(self, rules: Sequence[RiskRule], stressed_margin: Mapping[str, str], costs: TradeCosts | None = None):
        self.rules, self.stressed_margin, self.costs = tuple(rules), dict(stressed_margin), costs

    def evaluate(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskDecision:
        verdicts = (_input_verdict(proposal, book), *(_checked(r, proposal, book, market) for r in self.rules))
        return RiskDecision(
            book.name, proposal.trade_id, market.day.isoformat(), verdicts, self.stressed_margin,
            book.state.stale_marks, _entry_cash(self.costs, proposal, market), proposal,
        )  # fmt: skip
