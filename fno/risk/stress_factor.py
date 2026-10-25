"""The stress factor k in force on a decision day (story C2d): the latest row of A14c's append-only factor file dated
strictly before the day, so a replay of day d never sees a row written on d (judge 176); of two rows with the same date,
the later one in the file wins: the file is append-only, so it is the correction (judge 188). A held row keeps the old
factor in its `factor` column, so the row is read as written. Missing, malformed, too old or below 1 fails closed."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..constants import STRESS_FACTOR_COLUMNS, STRESS_FACTOR_DATE, STRESS_FACTOR_STATUSES
from .inputs import RiskInputError


@dataclass(frozen=True)
class FactorRow:
    as_of: date
    factor: float
    status: str
    evidence_sha256: str  # empty for the owner's seed row

    def record(self) -> dict[str, dict[str, str]]:
        """The row used, under its own key so its date and status never mix with the margin figures (story C2d)."""
        row = {"as_of": self.as_of.isoformat(), "factor": f"{self.factor:g}", "status": self.status,
               "evidence_sha256": self.evidence_sha256}  # fmt: skip
        return {"stress_factor_row": row}


def factor_in_force(path: Path, day: date, max_age_days: int) -> FactorRow:
    rows = [row for row in _rows(path) if row.as_of < day]
    if not rows:
        raise RiskInputError(f"stressed margin: {path.name} has no factor row before {day}")
    row = sorted(rows, key=lambda r: r.as_of)[-1]  # stable: of two same-day rows, the later one in the file
    if (day - row.as_of).days > max_age_days:
        raise RiskInputError(f"stressed margin multiplier of {row.as_of} is not valid on {day}")
    return row


def _rows(path: Path) -> list[FactorRow]:
    """Every row, checked: one unreadable row anywhere refuses the file by name (A14c appends it unattended)."""
    if not path.is_file():
        raise RiskInputError(f"stressed margin: the factor file {path.name} is missing")
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != STRESS_FACTOR_COLUMNS:
            raise RiskInputError(f"stressed margin: {path.name} columns must be {', '.join(STRESS_FACTOR_COLUMNS)}")
        return [_parsed(row, f"{path.name} row {number}") for number, row in enumerate(reader, 2)]


def _parsed(row: dict[str, str | None], where: str) -> FactorRow:
    try:
        as_of = datetime.strptime(row["as_of"] or "", STRESS_FACTOR_DATE).date()
        factor, status = float(row["factor"] or ""), row["status"]
    except (TypeError, ValueError) as exc:
        raise RiskInputError(f"stressed margin: {where} is unreadable ({exc})") from exc
    if not math.isfinite(factor) or factor < 1 or status not in STRESS_FACTOR_STATUSES:
        raise RiskInputError(f"stressed margin: {where} of {as_of} has factor {factor:g}, status {status!r}")
    return FactorRow(as_of, factor, status, row["evidence_sha256"] or "")
