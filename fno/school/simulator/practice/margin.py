"""The practice margin's stress factor (story MS-SIM-d2; orchestrator, 22 Oct: option A, law 3 is never skipped).

The pilot reads a factor in force on the session from `stress_factor.csv`, whose first row is 14 Oct 2026 and which is
valid for 30 days, so every earlier session would be refused. Practice uses the latest row for every session, on that
session's own archived SPAN file, and says so on every output."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

from ....risk.stress_factor import FactorRow, factor_in_force

SPAN_FIRST_DAY = date(2020, 1, 2)  # the first archived beginning-of-day SPAN file (`NseSpanBodSource.first_day`)
NO_SPAN_LINE = "{count} sessions refused: no SPAN archive before 2020 (the first file is 2020-01-02)"


def margin_label(row: FactorRow) -> str:
    """The label for the factor row actually used, never a fixed text that a later recompute would make false."""
    return (
        f"practice margin: stress factor {row.factor:g} (row of {row.as_of}, {row.status}; measured on NIFTY monthly "
        "only) on that day's archived SPAN; uses a factor computed after the fact"
    )


FAR_FUTURE = date(9999, 12, 31)  # the latest row is the one in force "then"
UNLIMITED_AGE_DAYS = 10**7


def latest_factor(path: Path) -> Callable[[date], FactorRow]:
    """A `date -> FactorRow` that ignores the date and returns the file's latest row (the file is read each time, so a
    missing or damaged file refuses the entry like the pilot's lookup does)."""

    def factor(_session: date) -> FactorRow:
        return latest_row(path)

    return factor


def latest_row(path: Path) -> FactorRow:
    return factor_in_force(path, FAR_FUTURE, UNLIMITED_AGE_DAYS)
