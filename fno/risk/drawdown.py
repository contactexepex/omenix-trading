"""The drawdown brake (owner decision of 12 Oct 2026, design 8, story C2).

When closed equity is the brake amount (Rs 30,000) or more below its high-water mark, no new trade opens; open trades
are never closed by the brake. Only the owner restarts it, with a `restart_brake` row in the book's
`owner_overrides.csv`; the brake then re-arms at the restart day's closing closed equity minus the brake amount, and the
high-water mark rises again from there. The full history is kept: a restart row on a day the brake was not in force is
an input error (the brake then refuses trades until the row is corrected), so a restart can never loosen a brake that
had not fired.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .inputs import Market, Proposal, RiskBook, RiskInputError
from .verdict import RiskRule, RiskVerdict, rupees

Series = Sequence[tuple[date, float]]  # (day, closed equity at that day's close), oldest first


def equity_at(series: Series, day: date) -> float:
    """Closed equity at the close of `day`: the last value recorded on or before it."""
    values = [value for d, value in series if d <= day]
    if not values:
        raise RiskInputError(f"no closed equity on or before {day}")
    return values[-1]


def high_water_mark(series: Series, restarts: Sequence[date], brake_rs: float) -> tuple[float, date | None]:
    """The high the brake measures from, and the restart day it starts at (None before any restart)."""
    if not series:
        raise RiskInputError("no closed equity recorded")
    anchor_day, high = None, series[0][1]
    for restart in restarts:
        high = max([high] + [v for d, v in series if (anchor_day is None or d > anchor_day) and d <= restart])
        restart_equity = equity_at(series, restart)
        if high - restart_equity < brake_rs:
            raise RiskInputError(f"owner restart on {restart}: the brake was not in force that day")
        anchor_day, high = restart, restart_equity
    later = [v for d, v in series if anchor_day is None or d > anchor_day]
    return max([high, *later]), anchor_day


class DrawdownBrake(RiskRule):
    name = "drawdown_brake"

    def __init__(self, brake_rs: float):
        self.brake_rs = brake_rs

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        high, restarted_on = high_water_mark(book.closed_equity, book.restarts, self.brake_rs)
        closed = book.state.closed_equity
        drawdown = high - closed
        numbers = {
            "closed_equity_rs": closed,
            "high_water_mark_rs": high,
            "drawdown_rs": drawdown,
            "brake_rs": self.brake_rs,
            "brake_level_rs": high - self.brake_rs,
            "restarted_on": restarted_on.isoformat() if restarted_on else "",
        }
        if drawdown >= self.brake_rs:
            reason = f"closed equity {rupees(closed)} is {rupees(drawdown)} below its high {rupees(high)}"
            return self.verdict(False, reason + "; new trades wait for the owner's restart", **numbers)
        return self.verdict(True, f"drawdown {rupees(drawdown)} is below the brake {rupees(self.brake_rs)}", **numbers)
