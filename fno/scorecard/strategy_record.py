"""One strategy version's paper record in one account (story E6), read from the account's own records only: E1's
ledger for the money, E4's desk records for which trade belongs to which version (`strategy`) and how each attempt
ended. A trade is a completed position when it opened and every leg has closed; an entry unwound at once (a partial
fill) is not a position, but its legging cost is real money of that version and stays in its ledgers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from ..accounting.ledgers import TradeLine, trade_line
from ..books.equity import trade_positions
from ..constants import OUTCOME_OPENED
from ..desk.execution import Holding
from ..desk.records import DeskRecords
from ..desk.status import open_positions


@dataclass(frozen=True)
class ClosedTrade:
    trade_id: str
    opened_on: date
    line: TradeLine  # C1's trade ledger line: gross, pads, charges, net, closed day
    completed: bool  # True: an opened position; False: an entry unwound at once (legging cost only)


@dataclass(frozen=True)
class OpenTrade:
    trade_id: str
    opened_on: date
    holdings: tuple[Holding, ...]
    cash_flow: float  # premium received minus paid, minus charges, so far


@dataclass(frozen=True)
class StrategyRecord:
    account: str  # a book, or a shadow account `shadow:<name>-v<n>`
    strategy: str  # `<name>-v<n>`
    closed: tuple[ClosedTrade, ...]
    open: tuple[OpenTrade, ...]
    fills: tuple[Mapping[str, str], ...]  # E4 desk fill rows
    events: tuple[Mapping[str, str], ...]  # E4 desk event rows

    @property
    def positions(self) -> tuple[ClosedTrade, ...]:
        """Completed positions: the sample a review judges (open ones are never counted)."""
        return tuple(t for t in self.closed if t.completed)

    @property
    def first_entry(self) -> date | None:
        days = [t.opened_on for t in (*self.closed, *self.open)]
        return min(days) if days else None


def strategy_records(account: str, records: DeskRecords, charges: Mapping[str, float]) -> list[StrategyRecord]:
    fills, events = records.fill_rows(), records.event_rows()
    trades = trade_positions(records.account.fills())
    opened = {e["trade_id"] for e in events if e["outcome"] == OUTCOME_OPENED}
    positions = open_positions(records)
    out = []
    for strategy in sorted({r["strategy"] for r in fills} | {e["strategy"] for e in events}):
        own = [r for r in fills if r["strategy"] == strategy]
        first_day = {}
        for row in own:
            day = date.fromisoformat(row["filled_at"][:10])
            first_day[row["trade_id"]] = min(day, first_day.get(row["trade_id"], day))
        closed = tuple(
            ClosedTrade(tid, first_day[tid], trade_line(trades[tid].as_ledger_trade(), dict(charges)), tid in opened)
            for tid in sorted(first_day) if not trades[tid].is_open
        )  # fmt: skip
        still_open = tuple(
            OpenTrade(p.trade_id, first_day[p.trade_id], p.holdings, p.cash_flow)
            for p in positions if p.strategy == strategy
        )  # fmt: skip
        own_events = tuple(e for e in events if e["strategy"] == strategy)
        out.append(StrategyRecord(account, strategy, closed, still_open, tuple(own), own_events))
    return out
