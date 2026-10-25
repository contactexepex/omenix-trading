"""The gate log (story R1): `research/factory/gates.csv`, one row per gate an idea reached, append-only.

B4's ledger keeps its ten columns, so an idea's status is the last row of its trial here. The guard refuses an edit or
deletion of any earlier row, in the working file or anywhere in its git history (D1's append-only check)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import astuple, dataclass
from pathlib import Path

from .append_only import AppendOnlyCsv, FileHistory
from .constants import GATE_COLUMNS, GATE_OUTCOMES, GATES_FILE, NUMBERS_PATTERN


class GateLogError(ValueError):
    """The gate log is refused: a bad row, or an earlier row edited or deleted."""


@dataclass(frozen=True)
class GateRow:
    trial_id: str
    gate: str
    outcome: str
    on: str  # ISO date the gate ran
    commit: str  # the commit the gate ran at
    numbers: str  # the gate's own figures as k=v;k=v, never a market value of a test's outcomes


def _check_row(row: GateRow) -> None:
    if not row.trial_id.isdigit():
        raise GateLogError(f"trial id {row.trial_id!r} is not a ledger trial number")
    if row.outcome not in GATE_OUTCOMES.get(row.gate, ()):
        raise GateLogError(f"trial {row.trial_id}: unknown gate {row.gate!r} or outcome {row.outcome!r}")
    if not re.match(NUMBERS_PATTERN, row.numbers):
        raise GateLogError(f"trial {row.trial_id}: numbers {row.numbers!r} are not k=v;k=v")


class GateLog:
    def __init__(self, root: Path, history: FileHistory):
        self.store = AppendOnlyCsv(root, GATES_FILE, GATE_COLUMNS, history, GateLogError)
        self.file = self.store.file

    def rows(self) -> list[GateRow]:
        rows = [GateRow(*line) for line in self.store.lines()]
        for row in rows:
            _check_row(row)
        return rows

    def last(self, trial_id: str) -> GateRow | None:
        mine = [row for row in self.rows() if row.trial_id == trial_id]
        return mine[-1] if mine else None

    def of_gate(self, gate: str) -> list[GateRow]:
        return [row for row in self.rows() if row.gate == gate]

    def history_problems(self) -> list[str]:
        return self.store.history_problems()

    def require_append_only(self) -> None:
        self.store.require_append_only()
        self.rows()  # every row valid

    def append(self, row: GateRow) -> None:
        self.prepare(row)()

    def prepare(self, row: GateRow) -> Callable[[], None]:
        """Checks the log and the row now and returns the append, which reads nothing (`AppendOnlyCsv.prepare`)."""
        self.rows()  # every row valid
        _check_row(row)
        return self.store.prepare(astuple(row))


def figures(row: GateRow) -> dict[str, str]:
    """The row's `numbers` as a mapping (k=v;k=v)."""
    return dict(pair.split("=", 1) for pair in row.numbers.split(";") if pair)
