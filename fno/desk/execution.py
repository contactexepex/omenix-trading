"""What entries, unwinds and exits share (story E4): a priced leg becomes E1's fill (C1's charges on the fill price)
with its desk row, at the snapshot's own time; and a position is closed short legs first, protection last.

Point in time: a snapshot may be priced from only once it has finished (never a quote from after the run's clock),
and a position is never closed at quotes captured before its last fill.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..accounting.ledgers import Order
from ..books.fills import Fill
from .pricing import FILL_PAD_RS, DeskLeg, LegQuote, price_leg
from .records import FillRecord
from .snapshot import ExecutionSnapshot, SnapshotError

PROTECTION_HELD = "protection held until every short leg is bought back"

Holding = tuple[DeskLeg, int]  # a leg and the units held (always positive; the leg's side says long or short)


def check_point_in_time(snapshot: ExecutionSnapshot, now: datetime, not_before: datetime | None = None) -> None:
    """Refuses a snapshot that finished after `now` (a later price) or before `not_before` (an older one: fills carry
    their snapshot's finish time, so a position's own snapshot is allowed and any earlier one is not)."""
    if snapshot.finished_at > now:
        raise SnapshotError(f"{snapshot.snapshot_id} finished at {snapshot.finished_at}, after the run's time {now}")
    if not_before is not None and snapshot.finished_at < not_before:
        raise SnapshotError(f"{snapshot.snapshot_id} finished at {snapshot.finished_at}, before {not_before}")


def fill_id(trade_id: str, action: str, contract: str) -> str:
    return f"{trade_id}:{action}:{contract}"


@dataclass(frozen=True)
class FillMaker:
    """Fills of one trade at one snapshot, priced by the one charges model (C1 through E1's `Fill.priced`)."""

    book: str
    strategy: str
    decision_id: str
    trade_id: str
    snapshot: ExecutionSnapshot
    charges: Mapping[str, float]

    def fill(self, quote: LegQuote, action: str) -> Fill:
        if not quote.fills:
            raise ValueError(f"{quote.leg.contract} has no price: {quote.reason}")
        order = Order(quote.side, quote.price, quote.units, FILL_PAD_RS)
        return Fill.priced(
            fill_id(self.trade_id, action, quote.leg.contract), self.trade_id, self.snapshot.finished_at,
            quote.leg.contract, order, dict(self.charges),
        )  # fmt: skip

    def record(self, quote: LegQuote, action: str) -> FillRecord:
        touch = quote.quote
        return FillRecord(
            self.book, self.strategy, self.decision_id, action, self.snapshot.snapshot_id, self.snapshot.sha256,
            quote.leg, touch.contract_id, touch.quote_age_unknown, self.fill(quote, action),
        )  # fmt: skip


def closing_quotes(snapshot: ExecutionSnapshot, holdings: Sequence[Holding]) -> tuple[list[LegQuote], list[LegQuote]]:
    """(legs that close now, legs left pending), in closing order: every short leg is bought back first; a protective
    leg is sold only once no short leg is left open, so a position is never left short without its protection."""
    shorts = [price_leg(snapshot, leg, leg.side(opening=False), units) for leg, units in holdings if not leg.protective]
    filled = [q for q in shorts if q.fills]
    pending = [q for q in shorts if not q.fills]
    for leg, units in (h for h in holdings if h[0].protective):
        quote = price_leg(snapshot, leg, leg.side(opening=False), units)
        if pending and quote.fills:
            quote = LegQuote(leg, quote.side, units, None, PROTECTION_HELD, quote.quote)
        (filled if quote.fills else pending).append(quote)
    return filled, pending


def legging_cost(fills: Sequence[Fill]) -> float:
    """Money lost by opening and unwinding legs: premium paid minus received, plus every charge."""
    return -sum(f.amount for f in fills)
