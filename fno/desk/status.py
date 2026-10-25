"""A book's open positions as the desk sees them (story E4), derived from the two append-only records and never kept
as separate state: E1's cash ledger says which trades are still open and what they hold; the desk events say which of
them must be exited, and which block the book's new risk: unverified protection, or a leg expired before its exit
(settlement needed, judge 68: its stale mark would otherwise let the book keep trading). A trade stops blocking the
book once its last leg is closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..books.equity import TradePosition, trade_positions
from ..constants import (
    OUTCOME_EXIT_ORDERED,
    OUTCOME_NOT_OPENED,
    OUTCOME_OPENED,
    OUTCOME_PARTIAL_FILL,
    OUTCOME_PROTECTION_UNVERIFIED,
    OUTCOME_REFUSED,
    OUTCOME_SETTLEMENT_NEEDED,
)
from .execution import Holding
from .records import DeskRecords

ENTRY_OUTCOMES = (OUTCOME_OPENED, OUTCOME_REFUSED, OUTCOME_NOT_OPENED, OUTCOME_PARTIAL_FILL)
BLOCKING_OUTCOMES = (OUTCOME_PROTECTION_UNVERIFIED, OUTCOME_SETTLEMENT_NEEDED)


@dataclass(frozen=True)
class OpenPosition:
    trade_id: str
    strategy: str
    decision_id: str
    holdings: tuple[Holding, ...]  # legs still held, with their units
    cash_flow: float  # E1: premium received minus paid, minus charges, so far
    last_fill_at: datetime
    opened_by: str  # snapshot ID of the trade's opening fills
    exit_reason: str  # why it must be exited (empty when no exit is ordered)
    blocks: tuple[str, ...]  # the blocking outcomes recorded for it (BLOCKING_OUTCOMES), in the order first seen


def _holdings(trade: TradePosition, records: DeskRecords) -> tuple[Holding, ...]:
    legs = records.legs(trade.trade_id)
    missing = [c for c, units in trade.units.items() if units and c not in legs]
    if missing:
        raise ValueError(f"trade {trade.trade_id}: no desk fill record for {', '.join(missing)}")
    return tuple((legs[c], abs(units)) for c, units in sorted(trade.units.items()) if units)


def open_positions(records: DeskRecords) -> list[OpenPosition]:
    positions = []
    for trade in (t for t in trade_positions(records.account.fills()).values() if t.is_open):
        events, fills = records.event_rows(trade.trade_id), records.fill_rows(trade.trade_id)
        ordered = [e["reason"] for e in events if e["outcome"] == OUTCOME_EXIT_ORDERED]
        blocks = tuple(dict.fromkeys(e["outcome"] for e in events if e["outcome"] in BLOCKING_OUTCOMES))
        positions.append(
            OpenPosition(
                trade.trade_id,
                fills[0]["strategy"],
                fills[0]["decision_id"],
                _holdings(trade, records),
                trade.cash_flow,
                max(f.filled_at for f in trade.fills),
                fills[0]["snapshot_id"],
                ordered[0] if ordered else "",
                blocks,
            )  # fmt: skip
        )
    return positions


def blocking_trades(records: DeskRecords) -> list[str]:
    """Open trades that block the book's new risk, each with why: while any is open, the book opens nothing new."""
    return [f"{p.trade_id} ({', '.join(p.blocks)})" for p in open_positions(records) if p.blocks]
