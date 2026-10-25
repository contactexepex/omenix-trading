"""A book's trades as scoreboard B scores them (story S2): E1's fills and C1's trade line for the money, E4's desk
records for the version and the decision, D3's committed record for the risk at entry and the segment, and each
session day's value while open. An entry unwound at once (a partial fill) is not a position, but its cost is the
book's money and stays in every total."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..accounting.ledgers import TradeLine, trade_line
from ..books.equity import trade_positions
from ..constants import OUTCOME_OPENED
from ..desk.pricing import DeskLeg
from ..desk.records import DeskRecords
from .daily_values import DayMarks, TradeDay, trade_days
from .entry_decisions import EntryDecisions
from .entry_facts import EntryFacts

OVERRIDDEN, NO_RECORD = "overridden", "unscored"
Sessions = Callable[[date, date], list[date]]  # the NSE sessions from one day to another, both included


@dataclass(frozen=True)
class ScoredTrade:
    trade_id: str
    strategy: str
    opened_on: date
    closed_on: date | None
    completed: bool  # an opened position (False: an entry unwound at once)
    line: TradeLine | None  # C1's trade ledger line once closed
    entry: EntryFacts | None  # None when the desk used no committed record for it
    days: tuple[TradeDay, ...]
    legs: tuple[DeskLeg, ...] = ()  # what it holds (story S6's random control draws twins of it)
    structure: str = ""  # the structure code its record names
    units: int = 0  # units per leg (lots x lot size)

    @property
    def group(self) -> str:
        """Where its results go: apart when overridden or unscored, else its D6 segment."""
        if self.entry is None:
            return NO_RECORD
        return OVERRIDDEN if self.entry.overridden else self.entry.segment.label


def book_trades(
    records: DeskRecords, decisions: EntryDecisions, sessions: Sessions, marks: DayMarks,
    charges: Mapping[str, float], on: date,
) -> list[ScoredTrade]:  # fmt: skip
    """Every trade the book has filled up to `on`, oldest first."""
    fills, rows = records.account.fills(), records.fill_rows()
    opened = {e["trade_id"] for e in records.event_rows() if e["outcome"] == OUTCOME_OPENED}
    out = []
    for trade_id, position in trade_positions(fills).items():
        own = [f for f in position.fills if f.filled_at.date() <= on]
        if not own:
            continue
        first = next(r for r in rows if r["trade_id"] == trade_id)
        start = own[0].filled_at.date()
        closed = position.closed_on if position.closed_on and position.closed_on <= on else None
        line = trade_line(position.as_ledger_trade(), dict(charges)) if closed else None
        entry = decisions.entry(records.account.book, start, first["decision_id"])
        legs = records.legs(trade_id)
        days = trade_days(own, legs, sessions(start, closed or on), marks)
        code = decisions.structure(records.account.book, start, first["decision_id"])
        out.append(ScoredTrade(trade_id, first["strategy"], start, closed, trade_id in opened, line, entry, days,
                               tuple(legs.values()), code, int(own[0].order.units)))  # fmt: skip
    return sorted(out, key=lambda t: (t.opened_on, t.trade_id))


def groups(trades: Sequence[ScoredTrade]) -> dict[str, list[ScoredTrade]]:
    found: dict[str, list[ScoredTrade]] = {}
    for trade in trades:
        found.setdefault(trade.group, []).append(trade)
    return dict(sorted(found.items()))
