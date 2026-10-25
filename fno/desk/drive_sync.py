"""E3's account writes with the private records in Drive (story E2c), behind E3's `AccountSync` port in place of
`GitAccountSync`. The daily run is the only account writer, so one write is: the book's journal under its lock, pulled
from Drive and pushed back (`open_account_writer`), then the book's public daily totals committed. No git reset or
reapply is needed: nothing else writes the account.

Drive failing (`PrivateFilesUnavailable`, a `CommitFailed`) stops the write: E3's one handler alerts and stops the run,
nothing is committed for the step, and the rerun repeats it (E1's fills are idempotent by fill ID, so nothing fills
twice)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from ..books.daily_totals import write_daily_totals
from .daily_ports import AccountSync, Committer
from .records import DeskJournal

T = TypeVar("T")


class DriveAccountSync(AccountSync):
    def __init__(self, open_journal: Callable[[str], object], committer: Committer, root: Path):
        self.open_journal, self.committer, self.root = open_journal, committer, Path(root)  # open_journal: E2c-aware

    def write(self, book: str, apply: Callable[[DeskJournal], T], message: str) -> T:
        with self.open_journal(book) as journal:
            result = apply(journal)
        self.committer.commit((write_daily_totals(self.root, book),), message)
        return result
