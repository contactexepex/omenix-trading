"""The daily stress line (story C5, design 6.2): every card shows, for all open positions, the loss under fixed
scenarios (`risk.stress_line`: NIFTY -5% and -10% overnight with VIX +50% and +100%, and +5%), next to the sum of
their maximum losses. It is a report, never a limit.

Each scenario is C2's full repricing (`StressEngine`): every leg revalued after one calendar day with NIFTY moved and
every leg's implied volatility multiplied by the scenario's factor (a VIX rise of 50% is applied as a 1.5 factor on
every leg's own volatility: reasoning only, the smile's change is not modelled). Two losses per scenario: from entry
(what the book would have lost in all, comparable with the maximum losses) and from today's marks (what tomorrow would
cost). Because every position is defined risk, the loss from entry before exit costs stays below the sum of maximum
losses; the line shows how close the book is to it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .inputs import Market, RiskBook
from .open_risk import PositionRisks
from .settings import Scenario
from .stress import Shock, StressEngine, stress_positions


@dataclass(frozen=True)
class StressRow:
    scenario: str
    loss_from_entry_rs: float
    loss_from_marks_rs: float


@dataclass(frozen=True)
class StressLine:
    book: str
    day: str
    rows: tuple[StressRow, ...]
    max_loss_sum_rs: float  # the open positions' maximum losses: what the -10% line can approach, never pass

    def record(self) -> dict:
        return {
            "book": self.book,
            "day": self.day,
            "max_loss_sum_rs": self.max_loss_sum_rs,
            "rows": [
                {"scenario": r.scenario, "loss_from_entry_rs": r.loss_from_entry_rs,
                 "loss_from_marks_rs": r.loss_from_marks_rs}
                for r in self.rows
            ],
        }  # fmt: skip


class DailyStressLine:
    def __init__(self, engine: StressEngine, risks: PositionRisks, scenarios: Sequence[Scenario]):
        self.engine, self.risks = engine, risks
        self.shocks = tuple(Shock.of(s) for s in scenarios)

    def line(self, book: RiskBook, market: Market) -> StressLine:
        results = self.engine.run(stress_positions(book, None), market, self.shocks)
        rows = tuple(StressRow(r.shock.name, r.loss_from_entry, r.loss_from_marks) for r in results)
        max_losses = sum(self.risks.of_open(t, market).max_loss_rs for t in book.open_trades)
        return StressLine(book.name, market.day.isoformat(), rows, max_losses)
