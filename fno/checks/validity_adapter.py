"""A book's C4 validator in the decision run (story C4): D2's chosen outcome turned into plain values and checked; the
failures are logged only when the run asks, after its records are written. It reads the trade as D2 recorded it (legs,
terms, the version and its claimed maximum loss) and the prices D2 used (the decision market's mids); everything it then
checks is recomputed in `validity*`, never taken from D2's code."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Protocol

from ..models import IST
from ..playbook.decision_validity import ValidityResult
from .data_checks import CaptureRecord
from .validity import ValidityChecker
from .validity_failures import ValidityFailureLog
from .validity_money import ProposedLeg
from .validity_proposal import ValidityLeg, ValidityProposal

if TYPE_CHECKING:
    from ..playbook.loader import Playbook
    from ..playbook.outcomes import Outcome
    from ..risk.inputs import Market, RiskBook


class CaptureSource(Protocol):
    def record(self, day: date) -> CaptureRecord | None: ...


def _legs(outcome: Outcome, market: Market) -> tuple[ValidityLeg, ...]:
    legs = []
    for proposed in outcome.candidate.proposal.legs:
        quote, leg = market.quote(proposed.contract), proposed.leg
        priced = ProposedLeg(leg.strike, leg.kind, leg.side, quote.mid)
        legs.append(ValidityLeg(proposed.contract, quote.expiry.isoformat(), priced))
    return tuple(legs)


def proposal_of(
    book: str, day: date, outcome: Outcome, market: Market, playbook: Playbook, cutoff: datetime
) -> ValidityProposal:
    """The chosen trade as C4 checks it. The version is the playbook's own file found by name and version, and the
    versions permitted are those the playbook approves on the day, not what the outcome says about itself."""
    candidate, opportunity = outcome.candidate, outcome.opportunity
    terms, named = candidate.proposal.terms, opportunity.strategy
    strategy = next((s for s in playbook.strategies if s.key == (named.name, named.version)), None)
    return ValidityProposal(
        book, opportunity.opportunity_id, day, cutoff, opportunity.context.expiry.isoformat(),
        terms.structure, terms.width, terms.lots, candidate.proposal.lot_size, _legs(outcome, market),
        candidate.max_loss, bool(outcome.risk and outcome.risk.ok), named.parameters_sha256, strategy,
        frozenset(s.key for s in playbook.approved_on(day)),
    )  # fmt: skip


def account_inputs(book: RiskBook) -> dict:
    """What C4 takes from the book as recorded inputs, not computations: each open trade's terms (recorded when it was
    decided) and the premium reserved for pending orders (E4)."""
    terms = {t.trade_id: (t.terms.structure, t.terms.width, t.terms.lots) for t in book.open_trades}
    return {"open_terms": terms, "premium_reserved": book.state.premium_reserved}


class BookTradeValidator:
    """D3's `TradeValidator` for one book. `log` is None in a replay, which must not write anything."""

    def __init__(
        self, book: str, checker: ValidityChecker, captures: CaptureSource, cutoff: time,
        log: ValidityFailureLog | None = None,
    ):  # fmt: skip
        self.book, self.checker, self.captures, self.cutoff, self.log = book, checker, captures, cutoff, log

    def validate(
        self, day: date, outcome: Outcome, market: Market, playbook: Playbook, book: RiskBook,
        earlier: tuple[Outcome, ...], eligible: frozenset[tuple[str, int]] = frozenset(),
    ) -> ValidityResult:  # fmt: skip
        cutoff = datetime.combine(day, self.cutoff, IST)
        before = tuple(proposal_of(self.book, day, o, market, playbook, cutoff) for o in earlier)
        own = proposal_of(self.book, day, outcome, market, playbook, cutoff)
        proposal = replace(own, earlier=before, eligible=eligible, **account_inputs(book))
        report = self.checker.check(proposal, self.captures.record(day))
        reason = "; ".join(f"{r.name}: {r.reason}" for r in report.failures)
        return ValidityResult(report.ok, report.record(), reason, report)

    def log_failures(self, day: date, results: Mapping[str, ValidityResult]) -> None:
        """Each report in the book's failure log (a pass writes nothing); the run calls it after writing its records."""
        if self.log is None:
            return
        for result in results.values():
            self.log.append(day, result.report)
