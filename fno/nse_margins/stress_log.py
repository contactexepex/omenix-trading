"""A14c's side of the stress factor file (`stress_factor.csv`, story C2d's columns): the last row as written, the
guardrails that decide the next row, and the append-only write. C2 and C4 read the file with their own readers.

Guardrails (owner, 15 Oct 2026, DESK_DECISIONS da0f769d; orchestrator: hold every fall): a result below 1.0 writes no
row; a result at or above the factor in force is applied at once; any lower result is held (the row keeps the old
factor and the alert asks the owner), unless the run cites the owner's DESK_DECISIONS commit approving that fall."""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import STRESS_FACTOR_COLUMNS

ROUND_STEP = 0.05  # the rule rounds the largest needed factor up to the next 0.05 (response 77)
APPLIED, HELD = "applied", "held"


class StressRowRefused(RuntimeError):
    """No row may be written, for the named reason."""


@dataclass(frozen=True)
class LastRow:
    factor: float
    unrounded: float | None  # None: the owner's seed (a hand value), so the next run is full
    coverage_through: date | None


@dataclass(frozen=True)
class NextRow:
    as_of: date
    factor: float
    computed: float
    unrounded: float
    status: str
    peak: str
    coverage_through: date
    evidence_sha256: str

    def as_csv_line(self) -> str:
        values = (self.as_of.isoformat(), f"{self.factor:g}", f"{self.computed:g}", f"{self.unrounded:.6f}",
                  self.status, self.peak, self.coverage_through.isoformat(), self.evidence_sha256)  # fmt: skip
        out = io.StringIO()
        csv.writer(out, lineterminator="\n").writerow(values)
        return out.getvalue()


def rounded_up(value: float) -> float:
    """Up to the next 0.05 (1.407 -> 1.45; 1.40 stays 1.40), free of float and bisection noise: the needed factor is
    kept to 6 decimals (`unrounded`), so a bisection end 1e-9 above 1.40 still gives 1.40."""
    return round(math.ceil(round(value / ROUND_STEP, 6)) * ROUND_STEP, 2)


def decide(last: LastRow, unrounded: float, approved_fall: str | None = None) -> tuple[float, float, str]:
    """(factor in force, computed, status) for a run whose largest needed factor is `unrounded`."""
    computed = rounded_up(unrounded)
    if computed < 1:
        raise StressRowRefused(f"the computed factor {computed:g} is below 1")
    if computed >= last.factor:
        return computed, computed, APPLIED
    if approved_fall:
        return computed, computed, APPLIED  # the owner approved this lower value (`peak` names the decision)
    return last.factor, computed, HELD


class StressFactorFile:
    def __init__(self, path: Path):
        self.path = path

    def last(self) -> LastRow:
        rows = self._rows()
        if not rows:
            raise StressRowRefused(f"{self.path.name} has no row: the owner's seed must be first (story C2d)")
        row = rows[-1]
        try:
            unrounded = float(row["unrounded"]) if row["unrounded"] else None
            through = date.fromisoformat(row["coverage_through"]) if row["coverage_through"] else None
            return LastRow(float(row["factor"]), unrounded, through)
        except (TypeError, ValueError) as exc:
            raise StressRowRefused(f"{self.path.name}: its last row is unreadable ({exc})") from exc

    def append(self, row: NextRow) -> None:
        """Appends one line; the bytes already there stay a prefix (never edited)."""
        data = self.path.read_bytes()
        with open(self.path, "ab") as fh:
            if data and not data.endswith(b"\n"):
                fh.write(b"\n")
            fh.write(row.as_csv_line().encode("utf-8"))

    def _rows(self) -> list[dict[str, str]]:
        if not self.path.is_file():
            raise StressRowRefused(f"{self.path.name} is missing")
        with open(self.path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if tuple(reader.fieldnames or ()) != STRESS_FACTOR_COLUMNS:
                raise StressRowRefused(f"{self.path.name}: columns must be {', '.join(STRESS_FACTOR_COLUMNS)}")
            return list(reader)
