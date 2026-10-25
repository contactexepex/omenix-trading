"""The step's account writes (story E8 rule 11): each book's journal under its lock, pulled from Drive and pushed back
(E2c), and its public daily totals rewritten. The totals are not committed here: the step returns them and the daily
run commits them with the step's run-log entry, in the run's one thread, through its one committer."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import TypeVar

from ...books.daily_totals import write_daily_totals
from ..daily_ports import AccountSync
from ..records import DeskJournal

T = TypeVar("T")


class StepAccountWrites(AccountSync):
    def __init__(self, open_journal: Callable[[str], AbstractContextManager[DeskJournal]], root: Path):
        self.open_journal, self.root, self.written = open_journal, Path(root), {}

    def write(self, book: str, apply: Callable[[DeskJournal], T], message: str) -> T:
        with self.open_journal(book) as journal:
            result = apply(journal)
        self.written[book] = write_daily_totals(self.root, book)
        return result

    def paths(self) -> tuple[Path, ...]:
        """Every daily-totals file this step rewrote, to commit with its run-log entry."""
        return tuple(self.written.values())
