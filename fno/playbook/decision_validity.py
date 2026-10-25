"""C4 inside the decision run (story D3's `validity.c4`, story C4): every trade D2 chose for the book is checked by
an independent validator before its record is written. A failure blocks the trade: its record keeps D2's outcome
and says "no trade, blocked by C4", and the day's chosen list leaves it out. Shadow outcomes and unchosen candidates
are not trades, so they are not checked. The same function runs in a replay, so the result is reproduced too. Checking
writes nothing: the run logs the failures only after its records are written (judge 84, must-fix D), so a rerun that
the store refuses as a duplicate leaves the failure log untouched."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Protocol

from ..constants import Decision

if TYPE_CHECKING:  # C4's validator imports this module and must not load D2's cost and structure code (story C4)
    from ..risk.inputs import Market, RiskBook
    from .loader import Playbook
    from .outcomes import DayEvaluation, Outcome

BLOCKED = "blocked by C4 hard validity"


@dataclass(frozen=True)
class ValidityResult:
    ok: bool
    record: dict  # every check with its numbers
    reason: str  # the failed checks, empty when it passed
    report: object = field(default=None, compare=False, repr=False)  # the validator's own report, for its failure log


class TradeValidator(Protocol):
    def validate(
        self, day: date, outcome: Outcome, market: Market, playbook: Playbook, book: RiskBook,
        earlier: tuple[Outcome, ...], eligible: frozenset[tuple[str, int]],
    ) -> ValidityResult: ...  # fmt: skip

    def log_failures(self, day: date, results: Mapping[str, ValidityResult]) -> None:
        """Called once the run's records are written; a replay's validator writes nothing."""


def validate_chosen(
    evaluation: DayEvaluation, validator: TradeValidator | None, market: Market, playbook: Playbook, book: RiskBook
) -> Mapping[str, ValidityResult]:
    """Each chosen book trade's C4 result by opportunity ID (empty without a validator), in opportunity-ID order. The
    trades chosen before it that passed count as entered, as D2 counts them; D2's eligible versions go with each (Book
    2's envelope chooses only among them, story D4). The day is the evaluation's own, never the
    market's: a stale market is then checked against the day's capture and fails."""
    if validator is None:
        return {}
    chosen = sorted(
        (o for o in evaluation.outcomes if o.decision == Decision.CHOSEN), key=lambda o: o.opportunity.opportunity_id
    )
    day, results, passed = date.fromisoformat(evaluation.day), {}, []
    for outcome in chosen:
        result = validator.validate(day, outcome, market, playbook, book, tuple(passed), evaluation.eligible)
        results[outcome.opportunity.opportunity_id] = result
        if result.ok:
            passed.append(outcome)
    return results
