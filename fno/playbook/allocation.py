"""Story D2's fixed allocation rule: valid candidates in rank order (expected net per rupee of maximum loss) compete for
the book's slots and cash. Each is checked by the risk manager (C2) against the book as it stands after the trades
already chosen today; an unproven version (fewer than 20 completed paper trades) holds at most one open trade. The
same rule runs for Book 1 and, separately, for each research candidate's own shadow book."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..constants import NO_TRADE_THRESHOLD_RS, UNPROVEN_BELOW_COMPLETED_TRADES, UNPROVEN_MAX_OPEN_TRADES, Decision
from ..risk.inputs import Market, RiskBook
from ..risk.manager import RiskDecision, RiskManager
from ..risk.trade_costs import TradeCosts
from .book_effects import book_after_entry
from .candidates import Candidate

SLOT_RULES, CASH_RULES = frozenset({"max_open_trades"}), frozenset({"margin_room"})


class StrategyTradeCounts(Protocol):
    """A book's paper trades of one strategy version (E5 records them; tests use a fake)."""

    def completed(self, name: str, version: int) -> int: ...

    def open(self, name: str, version: int) -> int: ...


Placed = tuple[Candidate, Decision, str, RiskDecision | None]


class Allocator:
    def __init__(self, risk: RiskManager, costs: TradeCosts):
        self.risk, self.costs = risk, costs

    def allocate(
        self,
        candidates: Sequence[Candidate],
        book: RiskBook,
        market: Market,
        counts: StrategyTradeCounts,
        threshold: bool = True,
    ) -> list[Placed]:
        """`threshold` False is the shadow forward test: the no-trade threshold binds paper allocation only, so the
        shadow records what the rule itself would do (orchestrator, 14 Oct 2026)."""
        placed: list[Placed] = []
        chosen_today: dict[tuple[str, int], int] = {}
        for rank, candidate in enumerate(sorted(candidates, key=Candidate.rank_key), start=1):
            key = candidate.opportunity.strategy.key
            refusal = self._before_risk(candidate, counts, chosen_today.get(key, 0), threshold)
            if refusal:
                placed.append((candidate, Decision.NOT_CHOSEN if refusal[0] else Decision.NO_TRADE, refusal[1], None))
                continue
            verdict = self.risk.evaluate(candidate.proposal, book, market)
            if not verdict.ok:
                placed.append((candidate, Decision.NOT_CHOSEN, _risk_reason(verdict), verdict))
                continue
            placed.append((candidate, Decision.CHOSEN, f"rank {rank}: score {candidate.score}", verdict))
            book = book_after_entry(book, candidate.proposal, market, self.costs)
            chosen_today[key] = chosen_today.get(key, 0) + 1
        return placed

    @staticmethod
    def _before_risk(
        candidate: Candidate, counts: StrategyTradeCounts, chosen: int, threshold: bool
    ) -> tuple[bool, str] | None:
        """(a valid candidate lost out, reason), or None when it may go to the risk check."""
        expected = candidate.expected_net
        if threshold and (expected is None or expected <= NO_TRADE_THRESHOLD_RS):
            return False, (
                f"expected net {expected} per opportunity is not above the no-trade threshold "
                f"{NO_TRADE_THRESHOLD_RS:g} after costs"
            )
        name, version = candidate.opportunity.strategy.key
        if counts.completed(name, version) < UNPROVEN_BELOW_COMPLETED_TRADES:
            holding = counts.open(name, version) + chosen
            if holding >= UNPROVEN_MAX_OPEN_TRADES:
                return True, (
                    f"unproven: {counts.completed(name, version)} completed paper trades (fewer than "
                    f"{UNPROVEN_BELOW_COMPLETED_TRADES}) and {holding} open, at most {UNPROVEN_MAX_OPEN_TRADES}"
                )
        return None


def _risk_reason(verdict: RiskDecision) -> str:
    failed = {v.rule for v in verdict.verdicts if not v.ok}
    kind = "slot" if failed <= SLOT_RULES else "cash" if failed <= CASH_RULES else "risk"
    return f"{kind}: " + "; ".join(verdict.reasons)
