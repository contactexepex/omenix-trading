"""An order's owner-timing fill in two steps (story E8 rules 2-9): `schedule` gives its due mark when it is sent (or
why it misses), and `price` reads that mark's snapshot once the mark has passed. Every leg is priced before any fill
(E4c's rule): one leg without a valid quote misses the whole entry ("missed, no quote"); E4c's entry check (a thin
size, protection not sellable back) and E4d's shared size then run at the mark's own copy and miss it with their own
code; an entry outside the owner's entry rule
is "missed, price moved". A miss is never retried at another mark or price."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from ..entries import EntryOrder
from ..entry_check import entry_problems, taken_units
from ..execution import FillMaker
from ..pricing import DeskLeg, LegQuote, price_leg
from ..snapshot import ExecutionSnapshot
from .clock import FillClock
from .entry_range import EntryRange
from .mark_levels import MarkSnapshot
from .mark_snapshots import MarkSnapshots
from .outcomes import ENTRY, MISSED_EXPIRED, MISSED_NO_QUOTE, MISSED_PRICE_MOVED, DueMark, Missed


@dataclass(frozen=True)
class PricedEntry:
    """Every leg of an entry priced at its due mark, inside the owner's entry rule: what the fill-day checks read."""

    due: DueMark
    mark: MarkSnapshot
    maker: FillMaker
    quotes: list[LegQuote]


class DueFill:
    def __init__(
        self, clock: FillClock, snapshots: MarkSnapshots, entry_range: EntryRange, charges: Mapping[str, float]
    ):
        self.clock, self.snapshots, self.entry_range = clock, snapshots, entry_range
        self.charges = dict(charges)

    def schedule(self, order: EntryOrder, sent_at: datetime) -> DueMark | Missed:
        due = self.clock.due(sent_at, ENTRY)
        if isinstance(due, DueMark) and due.session > order.expiry:
            return Missed(MISSED_EXPIRED)  # the contract stopped trading before the owner could act
        return due

    def price(
        self, order: EntryOrder, due: DueMark, book_fills: Iterable[Mapping[str, str]] = ()
    ) -> PricedEntry | Missed:
        """`book_fills`: the book's fill rows, so entries due at one mark share its displayed size (E4d)."""
        mark = self.snapshots.at(due.session, due.mark)
        if mark is None:
            return Missed(MISSED_NO_QUOTE)
        snapshot, units, trade_id, legs = mark.prices, order.proposal.units, order.proposal.trade_id, order.legs()
        if any(_unquoted(snapshot, leg) for leg in legs):
            return Missed(MISSED_NO_QUOTE, snapshot)
        problems = entry_problems(snapshot, legs, units, taken_units(book_fills, snapshot, trade_id))
        if problems:  # E4c and E4d at the mark's own copy: sizes, protection sellable back, the book's shared size
            return Missed(problems[0], snapshot)
        quotes = [price_leg(snapshot, leg, leg.side(opening=True), units) for leg in legs]
        maker = FillMaker(
            order.book, order.strategy, order.decision_id, order.proposal.trade_id, snapshot, self.charges
        )
        if not self.entry_range.admits(order, maker, quotes):
            return Missed(MISSED_PRICE_MOVED, snapshot)
        return PricedEntry(due, mark, maker, quotes)


def _unquoted(snapshot: ExecutionSnapshot, leg: DeskLeg) -> bool:
    """No valid quote to open the leg in this copy (judge 203 condition 3): none, no trade today, no price on the
    opening side, or crossed or sizeless. An empty far side (protection that could not be sold back) or a thin size is
    E4c's to name, with its own code (judge C's note on 09d14c43)."""
    quote = snapshot.quote(leg.expiry, leg.leg.strike, leg.leg.kind)
    if quote is None or not quote.valid or not quote.touch(leg.side(opening=True))[0]:
        return True
    return bool(quote.a4_problem) and bool(quote.bid and quote.ask)
