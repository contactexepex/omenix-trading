"""Each trade's value on each session day it is open (story S2): the cash it has moved so far (premiums and every
charge, from E1's fills) plus the legs it still holds at the mid of that day's execution snapshot, the marks E6 uses.

No price is invented: a leg without a valid mid keeps its last valid mark, flagged stale, and a leg never marked
leaves the day unvalued. The day a trade closes, its value is its cash flow alone, so the sum of its daily changes is
exactly its net in C1's trade ledger."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..books.fills import Fill
from ..desk.pricing import DeskLeg
from ..desk.snapshot import ContractKey

DayMarks = Callable[[date], Mapping[ContractKey, float]]  # a day's mid of every valid quote (empty when none)


@dataclass(frozen=True)
class TradeDay:
    day: date
    value: float | None  # None when a held leg has never had a valid mark
    stale: tuple[str, ...] = ()  # contracts valued at an earlier day's mark


def key_of(leg: DeskLeg) -> ContractKey:
    return leg.expiry, float(leg.leg.strike), leg.leg.kind


def trade_days(
    fills: Sequence[Fill], legs: Mapping[str, DeskLeg], sessions: Sequence[date], marks: DayMarks
) -> tuple[TradeDay, ...]:
    """The trade's value on each of `sessions` (its entry day to its close day, or to the report day if open)."""
    last: dict[str, float] = {}
    out = []
    for day in sessions:
        held: dict[str, int] = {}
        cash = 0.0
        for fill in (f for f in fills if f.filled_at.date() <= day):
            cash += fill.amount
            held[fill.contract] = held.get(fill.contract, 0) + fill.signed_units
        today = marks(day)
        value, stale = cash, []
        for contract, units in sorted(held.items()):
            if not units:
                continue
            mid = today.get(key_of(legs[contract]))
            if mid is not None:
                last[contract] = mid
            elif contract in last:
                stale.append(contract)
            else:
                value = None
                break
            value += units * last[contract]
        out.append(TradeDay(day, value, tuple(stale) if value is not None else ()))
    return tuple(out)


def daily_changes(days: Sequence[TradeDay]) -> dict[date, float]:
    """Each valued day's change from the last valued day (from zero before entry). An unvalued day has no change;
    the move across it lands on the next valued day, so the changes still add up to the last value."""
    changes, before = {}, 0.0
    for trade_day in days:
        if trade_day.value is not None:
            changes[trade_day.day] = trade_day.value - before
            before = trade_day.value
    return changes
