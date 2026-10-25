"""Which fired decisions trade, become tickets or are refused (story MS-P1f).

`classify` walks one driver's fired decisions at one slot in rank order (the card's frozen score, ties by the fixed
road order). Each is checked by the same safety laws through `check(decision, accepted)`, where `accepted` holds the
trades already taken this slot, so a law that adds up the slot (bucket, open risk, new risk a day, margin) sees them
before any fill (the fleet, MS-P1j, builds that running view). Only trades enter `accepted`: a ticket never takes a
place or adds risk to the running view.
- The first `max_new` that pass every law trade; a later one that passes is `ticket: trade_limit`.
- One refused only by account limits (`ACCOUNT_LIMITS`) is `ticket: account_limit`.
- Any other refusal is `refused`. The daily stop and the brake are not account limits here: a stopped or braked
  driver issues no tickets that day (`DRIVER_STOPS`).
- A refusal is named by a stop first, then by a trade-validity law, and by an account limit only when account limits
  alone refused, so a record never blames a cap for what a binding law stopped (judge 490).
- No law results at all is a wiring fault and raises: it never passes."""

from collections.abc import Callable
from dataclasses import replace

from ..constants import ACCOUNT_LIMITS, DRIVER_STOPS, Outcome, RefusalReason, TicketReason
from ..contracts.decisions import Decision
from ..contracts.roads import ROADS
from ..contracts.safety import LawResult

_ROAD_ORDER = {road.code: index for index, road in enumerate(ROADS)}

LawCheck = Callable[[Decision, tuple[Decision, ...]], tuple[LawResult, ...]]


def classify(fired: tuple[Decision, ...], check: LawCheck, max_new: int) -> tuple[tuple[Decision, tuple], ...]:
    """(decision after the laws, its law results) for every fired trade, in rank order. Decisions that are not
    trades (no trade, closed road, unavailable) are not passed here: they have no proposal to check."""
    if any(d.outcome != Outcome.TRADE for d in fired):
        raise ValueError("only fired trades are classified")
    accepted: list[Decision] = []
    out = []
    for decision in sorted(fired, key=lambda d: (-d.proposal.score, _ROAD_ORDER[d.road])):
        results = check(decision, tuple(accepted))
        if not results:
            raise ValueError(f"the law check returned no results for {decision.driver_id} on {decision.road}")
        final = _after_laws(decision, results, room=len(accepted) < max_new)
        if final.outcome == Outcome.TRADE:
            accepted.append(final)
        out.append((final, results))
    return tuple(out)


def _after_laws(decision: Decision, results: tuple[LawResult, ...], room: bool) -> Decision:
    refusals = [r.reason for r in results if not r.passed]
    if not refusals:
        return decision if room else as_ticket(decision, TicketReason.TRADE_LIMIT)
    if set(refusals) <= ACCOUNT_LIMITS:
        return as_ticket(decision, TicketReason.ACCOUNT_LIMIT)
    return replace(decision, outcome=Outcome.REFUSED, reason=named_refusal(refusals))


def named_refusal(refusals: list[RefusalReason]) -> RefusalReason:
    """The reason a record gives: a stop, else a trade-validity law, else (account limits alone) the first limit."""
    stops = [reason for reason in refusals if reason in DRIVER_STOPS]
    binding = [reason for reason in refusals if reason not in ACCOUNT_LIMITS]
    return (stops or binding or refusals)[0]


def ticket_laws_pass(results: tuple[LawResult, ...]) -> bool:
    """A ticket's laws: every refusal must be an account limit (relaxed for tickets) for it to stand. No results at
    all never pass."""
    return bool(results) and all(r.passed or r.reason in ACCOUNT_LIMITS for r in results)


def first_binding_refusal(results: tuple[LawResult, ...]) -> RefusalReason | None:
    """The refusal that binds a ticket (not an account limit), named as `named_refusal` names it, or None. Raises on
    no results: a ticket without its law results is a wiring fault, never a pass."""
    if not results:
        raise ValueError("a ticket's law results are missing")
    binding = [r.reason for r in results if not r.passed and r.reason not in ACCOUNT_LIMITS]
    return named_refusal(binding) if binding else None


def as_ticket(decision: Decision, reason: TicketReason) -> Decision:
    """Raises on a proposal of more than one lot: a driver bug (response 325 4.1 sizes every structure at one lot),
    which the fleet isolates as that driver's `unavailable: driver_error`."""
    if any(leg.lots != 1 for leg in decision.proposal.legs):
        raise ValueError("a ticket is one lot")
    return replace(decision, outcome=Outcome.TICKET, reason=reason)
