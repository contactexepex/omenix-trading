"""A closed position's outcome record (story 3.4): gross, costs and net in rupees from its own two fills, return on
risk against its maximum loss at entry, and slippage against the mids of the quotes the fills met. A mid is never
invented: an entry's mids are the quotes witnessed in its sealed decision record; an exit's are this slot's snapshot;
a settlement has none (it closes at intrinsic, not at a quote). A quote-based fill whose mid is unknown raises."""

from collections.abc import Mapping

from ..constants import SIDE_SELL, ExitReason, RoadCode
from ..contracts.accounts import FillResult, LedgerEntry
from ..contracts.records import ExitRecord, OutcomeRecord
from ..contracts.snapshot import ContractKey, SlotSnapshot

Mids = Mapping[ContractKey, float]
TICKET_PREFIX = "ticket:"


class MidUnknown(LookupError):
    """A quote-based fill's mid is not in what the fill met: no slippage figure is made up."""


def outcome_record(opening: LedgerEntry, closing: LedgerEntry, entry_mids: Mids, exit_mids: Mids,
                   is_ticket: bool) -> OutcomeRecord:  # fmt: skip
    if opening.position.position_id != closing.position.position_id or not closing.closes:
        raise ValueError("an outcome joins one position's opening and its closing")
    entry, exit_ = opening.fill, closing.fill
    gross = _premium(entry) + _premium(exit_)
    costs = sum(leg.charges for leg in (*entry.legs, *exit_.legs))
    net = entry.cash + exit_.cash
    settled = closing.exit_reason == ExitReason.EXPIRY
    slippage = _slippage(entry, entry_mids) + (0.0 if settled else _slippage(exit_, exit_mids))
    position = opening.position
    money = (gross, costs, net, net / position.max_loss, slippage)
    return OutcomeRecord(position.position_id, position.driver_id, position.road, entry.rests_on, entry, exit_,
                         closing.exit_reason, *money, is_ticket)  # fmt: skip


def _premium(fill: FillResult) -> float:
    return sum((leg.price if leg.side == SIDE_SELL else -leg.price) * leg.units for leg in fill.legs)


def _slippage(fill: FillResult, mids: Mids) -> float:
    """Rupees paid against the mids: buying above, or selling below, the mid."""
    total = 0.0
    for leg in fill.legs:
        if leg.key not in mids:
            raise MidUnknown(f"no mid for {leg.key.kind} {leg.key.strike:g} {leg.key.expiry}")
        edge = leg.price - mids[leg.key]
        total += (-edge if leg.side == SIDE_SELL else edge) * leg.units
    return total


def outcomes_of(books, exits: tuple[ExitRecord, ...], marks: Mapping[RoadCode, SlotSnapshot],
                entry_mids) -> tuple[OutcomeRecord, ...]:  # fmt: skip
    """The outcome of every exit record whose position its ledger shows closed, rebuilt from the ledger, so a rerun
    after a crash between the fills and the outcomes' seal seals the same records."""
    outcomes = []
    for exit_ in exits:
        ticket = exit_.position_id.startswith(TICKET_PREFIX)
        entries = (books.ticket_entries if ticket else books.account_entries).entries(exit_.driver_id)
        closings = [e for e in entries if e.closes and e.position.position_id == exit_.position_id]
        if not closings:
            continue  # it waits (no quote) or its settlement file is not out yet
        opening = next(e for e in entries if not e.closes and e.position.position_id == exit_.position_id)
        settled = exit_.exit_reason == ExitReason.EXPIRY
        snapshot = marks.get(exit_.road)
        exit_mids = {} if settled or snapshot is None else _mids(snapshot)
        outcomes.append(outcome_record(opening, closings[0], entry_mids(opening.position), exit_mids, ticket))
    return tuple(outcomes)


def _mids(snapshot: SlotSnapshot) -> dict[ContractKey, float]:
    return {key: quote.mid for key, quote in snapshot.quotes.items() if quote.mid is not None}
