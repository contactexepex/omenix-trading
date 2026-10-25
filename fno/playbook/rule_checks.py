"""Checks on a version's rule itself, whatever its status (research candidates included): they hold for every file the
loader reads, unlike the approval checks, which guard an approved status."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .fields import PlaybookError
from .schema import Strategy


class RuleCheck(ABC):
    @abstractmethod
    def check(self, strategy: Strategy) -> None:
        """PlaybookError unless the rule is acceptable."""


class CatastrophicCapWithinRisk(RuleCheck):
    """Story E6: the catastrophic-loss pause cap may not exceed the risk manager's per-trade maximum loss (C2, owner's
    Rs 10,000); a larger cap could never fire on a trade C2 let open (orchestrator, 14 Oct 2026)."""

    def __init__(self, max_loss_per_trade_rs: float):
        self.limit = max_loss_per_trade_rs

    def check(self, strategy: Strategy) -> None:
        cap = strategy.evaluation_plan["catastrophic_loss_rs"]
        if cap > self.limit:
            reason = f"Rs {cap:,.2f} is above the risk manager's per-trade maximum loss Rs {self.limit:,.2f}"
            raise PlaybookError("evaluation_plan.catastrophic_loss_rs", f"{reason}: it could never fire")
