"""Story D2: the day's rule evaluation and allocation, Book 1's decision. For each version approved (`paper`) at the
start of the day and not stopped since (a same-day approval trades from the next session; a pause or retirement stops
new entries at once), every opportunity today is evaluated on the live 15:00 feature values; a fired rule builds its
trade on live quotes, and the fixed allocation rule chooses among the valid candidates for the book's account. Each
research candidate registered before the day is evaluated the same way against its own shadow book (owner, 14 Oct
2026: forward shadow test), never Book 1's. A day with nothing approved allocates nothing; every opportunity, traded
or not, gets an outcome."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import date

from ..constants import Decision
from ..research_engine.features import DecisionContext, FeatureValue
from ..risk.inputs import Market, RiskBook
from .allocation import Allocator, StrategyTradeCounts
from .candidates import CandidateBuilder, NotBuilt
from .conditions import unmet_conditions
from .loader import Playbook
from .opportunities import BOOK, SHADOW, Opportunity, OpportunityFinder
from .outcomes import DayEvaluation, Outcome
from .shadow import RealBooks, ShadowBooks

SHADOW_DECISIONS = {Decision.CHOSEN: Decision.SHADOW_TRADE}


class LiveFeatureValues(ABC):
    @abstractmethod
    def values(self, day: date, context: DecisionContext) -> Mapping[str, FeatureValue]:
        """Every live 15:00 feature (B7) for this decision context, by live feature name; None when unknown."""


class RuleEvaluator:
    def __init__(self, finder: OpportunityFinder, builder: CandidateBuilder, allocator: Allocator, real: RealBooks):
        self.finder, self.builder, self.allocator, self.real = finder, builder, allocator, real

    def evaluate(
        self,
        day: date,
        playbook: Playbook,
        market: Market,
        features: LiveFeatureValues,
        book: RiskBook,
        counts: StrategyTradeCounts,
        shadow_books: ShadowBooks,
    ) -> DayEvaluation:
        monthly = tuple(market.futures)  # NIFTY futures list only the monthly expiries
        found = [o for s in playbook.approved_on(day) for o in self.finder.find(s, day, monthly, BOOK)]
        outcomes = self._allocate(day, found, market, features, book, counts)
        for strategy in playbook.shadow_on(day):  # each research candidate alone, in its own shadow book
            account = shadow_books.account(strategy)
            found = self.finder.find(strategy, day, monthly, SHADOW)
            overlap = self.real.overlap(account) or (account.book.name == book.name and "named like Book 1's book")
            if overlap:  # misconfigured: a shadow never draws on a real account
                outcomes += [_no_trade(o, {}, f"refused: {overlap}") for o in found]
                continue
            outcomes += self._allocate(day, found, market, features, account.book, account.counts, threshold=False)
        return DayEvaluation(day.isoformat(), book.name, tuple(sorted(outcomes, key=_order)))

    def _allocate(self, day, found, market, features, book, counts, threshold: bool = True) -> list[Outcome]:
        outcomes, candidates, seen = [], [], {}
        for opportunity in found:
            seen[opportunity.opportunity_id] = values = dict(features.values(day, opportunity.context))
            unmet = tuple(unmet_conditions(opportunity.strategy, values))
            if unmet:
                outcomes.append(_no_trade(opportunity, values, "rule did not fire", unmet))
                continue
            try:
                candidates.append(self.builder.build(opportunity, market, _trade_id(day, opportunity)))
            except NotBuilt as reason:
                outcomes.append(_no_trade(opportunity, values, str(reason)))
        for candidate, decision, reason, risk in self.allocator.allocate(candidates, book, market, counts, threshold):
            opportunity = candidate.opportunity
            if opportunity.mode == SHADOW:
                decision = SHADOW_DECISIONS.get(decision, Decision.SHADOW_NO_TRADE)
            outcomes.append(
                Outcome(opportunity, seen[opportunity.opportunity_id], decision, reason, (), candidate, risk)
            )
        return outcomes


def _no_trade(opportunity: Opportunity, values, reason: str, unmet: tuple[str, ...] = ()) -> Outcome:
    decision = Decision.SHADOW_NO_TRADE if opportunity.mode == SHADOW else Decision.NO_TRADE
    return Outcome(opportunity, values, decision, reason, unmet)


def _trade_id(day: date, opportunity: Opportunity) -> str:
    prefix = "shadow-" if opportunity.mode == SHADOW else ""
    return f"{prefix}{day.isoformat()}-{opportunity.opportunity_id}"


def _order(outcome: Outcome) -> tuple:
    return outcome.opportunity.mode != BOOK, outcome.opportunity.opportunity_id
