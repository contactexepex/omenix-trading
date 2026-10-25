"""C4's own reader of the stress factor (story C2d): the latest row of A14c's factor file dated strictly before the
decision day, by the same rule as C2 but written apart (story C4: no C2 code). Fails closed by name."""

from __future__ import annotations

import csv
import math
from datetime import date, datetime
from pathlib import Path

from ..constants import STRESS_FACTOR_COLUMNS, STRESS_FACTOR_DATE, STRESS_FACTOR_STATUSES


class FactorProblem(ValueError):
    """No usable stress factor for the day, for the named reason."""


def factor_on(path: Path | None, day: date, max_age_days: int) -> tuple[date, float]:
    """(as_of, factor) of the row in force on `day`; of two same-day rows the later one in the file (append-only)."""
    before = [row for row in _rows(path) if row[0] < day]
    if not before:
        raise FactorProblem(f"stressed margin: {path.name} has no factor row before {day}")
    as_of, factor = sorted(before, key=lambda row: row[0])[-1]  # a stable sort keeps the file's order within a day
    if (day - as_of).days > max_age_days:
        raise FactorProblem(f"stressed margin multiplier of {as_of} is not valid on {day}")
    return as_of, factor


def _rows(path: Path | None) -> list[tuple[date, float]]:
    """Every row, checked: one unreadable row anywhere refuses the file by name."""
    if path is None:
        raise FactorProblem("stressed margin multiplier is not set (risk.stressed_margin.factor_file is required)")
    if not path.is_file():
        raise FactorProblem(f"stressed margin: the factor file {path.name} is missing")
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != STRESS_FACTOR_COLUMNS:
            raise FactorProblem(f"stressed margin: {path.name} columns must be {', '.join(STRESS_FACTOR_COLUMNS)}")
        return [_row(row, f"{path.name} row {number}") for number, row in enumerate(reader, 2)]


def _row(row: dict[str, str | None], where: str) -> tuple[date, float]:
    try:
        as_of = datetime.strptime(row["as_of"] or "", STRESS_FACTOR_DATE).date()
        factor = float(row["factor"] or "")
    except (TypeError, ValueError) as exc:
        raise FactorProblem(f"stressed margin: {where} is unreadable ({exc})") from exc
    status = row["status"]
    if not math.isfinite(factor) or factor < 1 or status not in STRESS_FACTOR_STATUSES:
        raise FactorProblem(f"stressed margin: {where} of {as_of} has factor {factor:g}, status {status!r}")
    return as_of, factor
