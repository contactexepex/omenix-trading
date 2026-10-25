"""Missed forecasts (PROTOCOL_v4.md section 4, revision 9; owner decisions of 15 Oct 2026).

Verdicts use observed days only (`pairs.py` never imputes). This counts what the scored set leaves out, so a member
cannot gain by missing hard days:

- **Not started:** days before the forecaster's first forecast are neither scored nor missed.
- **Miss:** a resolved, non-void day where the primary baseline forecast and the forecaster did not (a null answer is
  a miss).
- **Input failure:** a resolved, non-void day where neither forecast (the common pack failed); counted apart, never a
  miss, never eligible.
- **Undecided, operations:** more than `MISS_CAP` of the baseline-observable days missed, or more than
  `BIG_DAY_MISS_CAP` of the baseline-observable 2% days missed (so with fewer than 10 such days, any miss: one miss
  is already more than 10%). Such a member is not judged at the look: never a claim and never futile, so it keeps
  Test A undecided.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from .pairs import DatedForecasts
from .terms import BIG_DAY_MISS_CAP, MISS_CAP


@dataclass(frozen=True)
class MissReport:
    observable: int  # baseline-observable days from the first forecast on
    missed: int
    big_observable: int  # of them, 2% days
    big_missed: int
    input_failures: int

    @property
    def operations_undecided(self) -> bool:
        return self.missed > MISS_CAP * self.observable or self.big_missed > BIG_DAY_MISS_CAP * self.big_observable

    def line(self) -> str:
        share = f" ({100 * self.missed / self.observable:.1f}%)" if self.observable else ""
        verdict = "; undecided, operations" if self.operations_undecided else ""
        return (f"misses: {self.missed} of {self.observable} baseline days{share}, {self.big_missed} of "
                f"{self.big_observable} 2% days; input failures: {self.input_failures}{verdict}")  # fmt: skip


def miss_report(
    rows: Sequence[DatedForecasts], big_day: Callable[[date], bool], start: date | None = None
) -> MissReport:
    """`big_day(d)`: whether day d's regime return is a 2% move (the same input as the scored window's regime).
    `start`: the day misses count from when the rows begin later than the forecaster did (after the freeze, rows hold
    only later days, so a member that breaks straight after it must still count those days; judge 149 review);
    default: the first forecast in the rows."""
    started = [r for r in sorted(rows, key=lambda r: r.day) if r.forecast is not None]
    first = start or (started[0].day if started else None)
    counted = [r for r in rows if first is not None and r.day >= first and r.outcome is not None and not r.void]
    observable = [r for r in counted if r.baseline is not None]
    missed = [r for r in observable if r.forecast is None]
    return MissReport(
        len(observable),
        len(missed),
        sum(big_day(r.day) for r in observable),
        sum(big_day(r.day) for r in missed),
        sum(r.forecast is None and r.baseline is None for r in counted),
    )
