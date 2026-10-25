"""Story G11 C8, BG1's budget stop for the AI books' v4 fire: the AI forecasters stop **last** (`BG-budget.md`, design
7.6: analysts, idea generator, post-mortem writer, devil's advocate, AI forecasters last). BG1's level is one flag for
every role, and the roles before the forecasters already stop on it, so the books stop only when stopping every other
role cannot help: the month's level is `stop` **and** the books' own minutes (BG1's ledger rows with a book) reach the
cap by themselves. Then the day is `not_fired`, a miss.

The reading is BG1's own meter (`budget.wiring.build_month_meter`: its ledger, its cap), never a copy and never the
signal file, which no schedule writes yet. A meter that cannot be read fires the books with one #fno-desk line (fail
open: a miss costs the slot under the 10% cap). Both choices are the builder's recommendation pending the owner's
ruling (orchestrator, 24 Oct): each is the one line marked below."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from ..budget.constants import BUDGET_STOP
from ..budget.report import MonthMeter

BOOKS_STOP = "BG1 stop: {month}'s level is stop and the books alone used {books:,.2f} of {cap:,.2f} cap minutes"
NO_READING = "no BG1 reading for {month} ({why}): the books are fired (fail open)"


@dataclass(frozen=True)
class BudgetCheck:
    stop: str  # why the books are not fired today; '' when they may be
    note: str  # one line for #fno-desk when the reading itself failed; '' otherwise


class BudgetStop(ABC):
    @abstractmethod
    def check(self, day: date) -> BudgetCheck:
        """Whether the month's budget lets the AI books fire on `day`."""


@dataclass
class MeterBudgetStop(BudgetStop):
    meter: Callable[[str, date], MonthMeter]  # BG1's month meter for (YYYY-MM, today)

    def check(self, day: date) -> BudgetCheck:
        month = f"{day:%Y-%m}"
        try:
            reading = self.meter(month, day)
        except (ValueError, OSError, KeyError) as why:
            return BudgetCheck("", NO_READING.format(month=month, why=why))  # the owner's call: fail open
        books = sum(float(row["minutes"]) for row in reading.usage_rows if row.get("book"))
        cap = reading.cap.cap_minutes
        if reading.cap.level == BUDGET_STOP and books >= cap:  # the owner's call: forecasters last
            return BudgetCheck(BOOKS_STOP.format(month=month, books=books, cap=cap), "")
        return BudgetCheck("", "")
