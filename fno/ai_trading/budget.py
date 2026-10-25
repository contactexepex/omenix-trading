"""The trading decisions' budget stop (story F1t revision 2, judge 623 should-fix 2): a second implementation of G11's
`BudgetStop`, reading the same BG1 month meter. Decisions stop as soon as the month's level is `stop` (design 7.6:
the AI forecasters stop last, so every other AI role, the decisions among them, stops first); G11's `MeterBudgetStop`
stops the forecasters only when the books' own minutes also reach the cap. A meter that cannot be read fires the books
with a note for the step's alert: a deliberate fail-open on cost only (orchestrator, 25 Oct; owner's "no AI cap,
unlimited"), since every trade still passes C2, C4, the envelope or constitution and the judge."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from ..ai.budget_stop import BudgetCheck, BudgetStop
from ..budget.constants import BUDGET_STOP
from ..budget.report import MonthMeter

LEVEL_STOP = "BG1 stop: {month}'s budget level is stop (AI trading decisions stop before the forecasters)"
NO_READING = "no BG1 reading for {month} ({why}): the decision routines are fired (fail open, cost only)"


@dataclass
class LevelBudgetStop(BudgetStop):
    meter: Callable[[str, date], MonthMeter]  # BG1's month meter for (YYYY-MM, today)

    def check(self, day: date) -> BudgetCheck:
        month = f"{day:%Y-%m}"
        try:
            reading = self.meter(month, day)
        except Exception as why:  # noqa: BLE001 - any unreadable meter (a null `budget:` too) fails open on cost only
            return BudgetCheck("", NO_READING.format(month=month, why=f"{type(why).__name__}: {why}"))
        return BudgetCheck(LEVEL_STOP.format(month=month) if reading.cap.level == BUDGET_STOP else "", "")
