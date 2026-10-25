"""The mandatory control roles' score (story F9a; design 3.1 and 13.6): caught violations and prevented invalid actions
from C4's failure log, never a profit figure. A caught violation is one failed check; a prevented action is one
blocked (day, opportunity). C2's limits are counted through the C4 checks that enforce them; C3 keeps no per-book
refusal log, so its refusals are not counted (Known limits)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

from ..checks.validity_failures import ValidityFailureLog


@dataclass(frozen=True)
class ControlCounts:
    caught_violations: int
    prevented_actions: int
    by_check: dict[str, int]


def control_counts(log: ValidityFailureLog, book: str, first: date, last: date) -> ControlCounts:
    path = log.path(book)
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))) if path.is_file() else []
    rows = [r for r in rows if first.isoformat() <= r["day"] <= last.isoformat()]
    by_check: dict[str, int] = {}
    for row in rows:
        by_check[row["check"]] = by_check.get(row["check"], 0) + 1
    prevented = {(r["day"], r["opportunity_id"]) for r in rows}
    return ControlCounts(len(rows), len(prevented), dict(sorted(by_check.items())))
