"""The three counts (327 item 1): per (session, road, driver version) from its one sealed decision, the laws it met
and its fill. Every scheduled decision is counted, so refusals, closed roads and missing fills stay in the
denominator (`scheduled`)."""

from collections.abc import Iterable
from dataclasses import dataclass

from ..constants import Outcome
from ..contracts.accounts import FillResult
from ..contracts.decisions import Decision
from ..contracts.safety import LawResult
from ..contracts.tickets import OpportunityCounts
from .rules import ticket_laws_pass


def counts_for(decision: Decision, results: tuple[LawResult, ...], fill: FillResult | None,
               size_shared: bool = False) -> OpportunityCounts:  # fmt: skip
    """Eligible: the rule fired and a structure was built. Fillable: its laws passed (a ticket's with the account
    limits relaxed) and it filled at the touch, in the account or the ticket ledger. Executed: filled in the account.
    An account entry the shared displayed size could not serve (`size_shared`) is fillable but not executed.
    A decision `unavailable` after its rule fired (e.g. a seal failure) carries no proposal: not eligible, but it
    stays in `scheduled`."""
    if decision.outcome in (Outcome.TRADE, Outcome.TICKET) and not results:
        raise ValueError("a trade or ticket is counted with its law results: none means the laws never ran")
    eligible = decision.proposal is not None
    filled = fill is not None and fill.filled
    laws = ticket_laws_pass(results) if decision.outcome == Outcome.TICKET else all(r.passed for r in results)
    fillable = decision.outcome in (Outcome.TRADE, Outcome.TICKET) and laws and filled  # both carry a proposal
    executed = fillable and decision.outcome == Outcome.TRADE and not size_shared
    return OpportunityCounts(decision.session, decision.road, decision.driver_id, int(eligible), int(fillable),
                             int(executed))  # fmt: skip


@dataclass(frozen=True)
class CountTotals:
    scheduled: int  # every sealed decision: the denominator of every report
    eligible: int
    fillable: int
    executed: int


def totals(counts: Iterable[OpportunityCounts]) -> CountTotals:
    """Refuses a second row for one (session, road, driver): it would inflate the denominator."""
    rows = list(counts)
    if len({(c.session, c.road, c.driver_id) for c in rows}) != len(rows):
        raise ValueError("one counts row per (session, road, driver version)")
    return CountTotals(len(rows), sum(c.eligible for c in rows), sum(c.fillable for c in rows),
                       sum(c.executed for c in rows))  # fmt: skip
