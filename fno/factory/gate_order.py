"""The checks every gate after G0 shares (story R1): it runs once, in order, on a card whose inputs are committed, with
nothing but its own files staged, and logs one gate-log row. A measurement (B0, FT1) never passes a gate after G0
(R3's registration procedure, step 1)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from typing import Protocol

from .card import IdeaCard
from .constants import GATES_FILE, Gate, Outcome
from .gate_log import GateLog, GateRow


class GateStepError(ValueError):
    """The gate did not run; nothing was logged."""


class StepGit(Protocol):
    def head(self) -> str: ...

    def staged_paths(self) -> list[str]: ...

    def tree_matches(self, commit: str, paths: tuple[str, ...]) -> bool: ...

    def is_ancestor(self, older: str, newer: str) -> bool: ...

    def unchanged_since(self, commit: str, path: str) -> bool: ...


class GateOrder:
    def __init__(self, gates: GateLog, git: StepGit):
        self.gates, self.git = gates, git

    def ready(self, card: IdeaCard, after: Gate, outcomes: tuple[Outcome, ...], staged: Iterable[str] = ()) -> None:
        if card.measurement:
            raise GateStepError(f"{card.path}: a measurement is never screened (R3 registration, step 1)")
        others = sorted(set(self.git.staged_paths()) - {GATES_FILE, *staged})
        if others:
            raise GateStepError(f"other files are staged ({', '.join(others)}): commit them first")
        if not self.git.tree_matches(self.git.head(), (card.path,)):
            raise GateStepError(f"{card.path} has uncommitted changes: commit its inputs before its gate runs")
        self.gates.require_append_only()
        last = self.gates.last(card.trial_id)
        if last is None or last.gate != after or last.outcome not in outcomes:
            reached = f"{last.gate} {last.outcome}" if last else "no gate"
            wanted = " or ".join(f"{after} {outcome}" for outcome in outcomes)
            raise GateStepError(f"trial {card.trial_id}: its last gate is {reached}; this gate runs after {wanted}")

    def row(self, trial_id: str, gate: Gate) -> GateRow:
        return next(row for row in self.gates.rows() if row.trial_id == trial_id and row.gate == gate)

    def log(self, card: IdeaCard, gate: Gate, outcome: Outcome, today: date, numbers: str) -> GateRow:
        row, write = self.prepare(card, gate, outcome, today, numbers, self.git.head())
        write()
        return row

    def prepare(self, card: IdeaCard, gate: Gate, outcome: Outcome, today: date, numbers: str, commit: str
                ) -> tuple[GateRow, Callable[[], None]]:  # fmt: skip
        """The row at `commit` and its append, every check done now: a gate with another write reads git first."""
        row = GateRow(card.trial_id, gate, outcome, today.isoformat(), commit, numbers)
        return row, self.gates.prepare(row)
