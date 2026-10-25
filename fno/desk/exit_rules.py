"""Exit rules (story E4): each says whether an open position must close now, from its value at the execution
snapshot. Their numbers come from the strategy's playbook version (D1); the desk only applies them.

The value is what closing every leg at this snapshot's touch would leave: the trade's cash flow so far plus the closing
fills' cash, every C1 charge included. When a leg has no valid quote the value is unknown (None): a price rule cannot be
judged and does not fire on a guess; the time rule still does.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta

from .status import OpenPosition

# Public reasons (desk_events.csv) carry no quote-derived figure: the net if closed now, with the other legs' published
# close fills, gives a pending leg's touch at a snapshot where it did not fill (decision 48, story E2b).
TARGET_REACHED = "the net if closed now reaches the profit target"
STOP_REACHED = "the net if closed now reaches the stop loss"


@dataclass(frozen=True)
class ExitContext:
    day: date
    net_if_closed_rs: float | None  # the trade's net P&L if every leg closed now at the touch; None if unquotable


class ExitRule(ABC):
    name: str

    @abstractmethod
    def reached(self, position: OpenPosition, context: ExitContext) -> str:
        """Why the position must close now, or empty."""


class ProfitTarget(ExitRule):
    name = "profit_target"

    def __init__(self, target_rs: float):
        self.target_rs = target_rs

    def reached(self, position: OpenPosition, context: ExitContext) -> str:
        net = context.net_if_closed_rs
        if net is None or net < self.target_rs:
            return ""
        return f"{self.name}: {TARGET_REACHED}"


class StopLoss(ExitRule):
    name = "stop_loss"

    def __init__(self, loss_rs: float):
        self.loss_rs = loss_rs

    def reached(self, position: OpenPosition, context: ExitContext) -> str:
        net = context.net_if_closed_rs
        if net is None or net > -self.loss_rs:
            return ""
        return f"{self.name}: {STOP_REACHED}"


class TimeExit(ExitRule):
    """Close on or after `days_before_expiry` calendar days before the position's nearest expiry (0: expiry day)."""

    name = "time_exit"

    def __init__(self, days_before_expiry: int):
        if days_before_expiry < 0:
            raise ValueError("days_before_expiry cannot be negative")
        self.days = days_before_expiry

    def reached(self, position: OpenPosition, context: ExitContext) -> str:
        expiry = min(leg.expiry for leg, _ in position.holdings)
        exit_day = expiry - timedelta(days=self.days)
        if context.day < exit_day:
            return ""
        return f"{self.name}: {context.day} is on or after {exit_day} ({self.days} days before expiry {expiry})"


class ExitOnDay(ExitRule):
    """Close on or after a fixed trading day: a playbook version's time exit as D2 computed it (story E5)."""

    name = "time_exit"

    def __init__(self, exit_day: date, why: str):
        self.exit_day, self.why = exit_day, why

    def reached(self, position: OpenPosition, context: ExitContext) -> str:
        if context.day < self.exit_day:
            return ""
        return f"{self.name}: {context.day} is on or after {self.exit_day} ({self.why})"
