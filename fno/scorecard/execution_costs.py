"""Execution costs measured from the paper record (story E6, criterion 3), against what research assumed:

- **half-spread paid** per unit: a buy at the ask pays ask - mid, a sell at the bid pays mid - bid (mid of the touch it
  filled against, read from the execution snapshot the fill row names: `touches.py`, story E2b), averaged over every
  unit traded at a known touch (settlements have no quote), next to research's Rs 1 pad (B2);
- **legging costs**: what entries unwound at once (partial fills) cost, from E4's events;
- **not filled**: the share of attempts that reached the fill step and did not open (a leg without a valid quote or
  size, or an entry worse than approved); gate refusals (C2, timing, a blocked book) are counted apart;
- **pending exits**: how long exits waited for valid quotes, in calendar days from the exit order to the close (or
  to today for one still waiting).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from ..constants import (
    OUTCOME_CLOSED,
    OUTCOME_EXIT_ORDERED,
    OUTCOME_NOT_OPENED,
    OUTCOME_OPENED,
    OUTCOME_PARTIAL_FILL,
    OUTCOME_PENDING_EXIT,
    OUTCOME_REFUSED,
)
from ..desk.snapshot import ExecutionSnapshotSource
from ..research_engine.cycle_costs import PAD
from .strategy_record import StrategyRecord
from .touches import half_spread

RESEARCH_PAD_RS = PAD  # rupees per unit, every leg, entry and exit (B2)


@dataclass(frozen=True)
class ExecutionCosts:
    units_at_quotes: int
    half_spread_per_unit: float | None  # None when nothing traded at a known touch yet
    touch_unknown: int  # fills whose touch could not be read from their snapshot (story E2b)
    research_pad_per_unit: float
    legging_costs_rs: float
    attempts: int  # entries that reached the fill step
    opened: int
    not_filled: int  # not opened plus partial fills
    refused: int  # stopped by a gate before any leg was priced
    pending_exits: int  # trades whose exit had to wait
    pending_days: tuple[int, ...]  # each wait in calendar days (to today when still waiting)
    still_pending: tuple[str, ...]

    @property
    def not_filled_share(self) -> float | None:
        return self.not_filled / self.attempts if self.attempts else None

    @property
    def mean_pending_days(self) -> float | None:
        return sum(self.pending_days) / len(self.pending_days) if self.pending_days else None


def _pending(events: Sequence, today: date) -> tuple[list[int], list[str]]:
    days, waiting = [], []
    for trade_id in sorted({e["trade_id"] for e in events if e["outcome"] == OUTCOME_PENDING_EXIT}):
        own = [e for e in events if e["trade_id"] == trade_id]
        ordered = min(date.fromisoformat(e["day"]) for e in own if e["outcome"] == OUTCOME_EXIT_ORDERED)
        closed = [date.fromisoformat(e["day"]) for e in own if e["outcome"] == OUTCOME_CLOSED]
        days.append(((closed[0] if closed else today) - ordered).days)
        if not closed:
            waiting.append(trade_id)
    return days, waiting


def execution_costs(record: StrategyRecord, today: date, snapshots: ExecutionSnapshotSource) -> ExecutionCosts:
    outcomes = [e["outcome"] for e in record.events]
    spread = half_spread(record.fills, snapshots)
    legging = sum(float(e["legging_cost_rs"]) for e in record.events if e["legging_cost_rs"])
    not_filled = outcomes.count(OUTCOME_NOT_OPENED) + outcomes.count(OUTCOME_PARTIAL_FILL)
    days, waiting = _pending(record.events, today)
    return ExecutionCosts(
        spread.units, spread.per_unit, spread.touch_unknown, RESEARCH_PAD_RS, legging,
        not_filled + outcomes.count(OUTCOME_OPENED),
        outcomes.count(OUTCOME_OPENED), not_filled, outcomes.count(OUTCOME_REFUSED), len(days), tuple(days),
        tuple(waiting),
    )  # fmt: skip
