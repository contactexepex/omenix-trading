"""The AI books' minutes in BG1's usage ledger (story F8c; written by the G11 builder, 013xqaNT, and moved here): each
book's routine publishes its own timing of the run from its `reveal` step (`run_timing.py`, `timing_path`); the
Actions side reads every timing file with BG1's own reader (`SelfTimedUsageReader`) and records it in
`accounting/ai_usage.csv` as books-and-roles use of that book. The ledger records a session-day once, so every file is
offered on every run: one that landed after a collect is recorded by the next. A bad file is a refused line, never a
traceback and never a guessed row."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..budget.constants import PURPOSE_BOOKS_AND_ROLES
from ..budget.self_timed import SelfTimedUsageReader
from ..budget.usage_ledger import Attribution, UsageLedger, UsageRefused
from ..budget.usage_reader import ExportRefused
from ..constants import AI_BOOKS
from .paths import AI_FOLDER

TIMING_GLOB = "timing/*/*.timing.json"
RUN_ROLES = {"": "", "decision": "{book} trading decision"}  # a run's name in its timing file -> its usage role
LINE = "Omenix F&O AI books' minutes (BG1): {file}: {result}"
ALREADY = "already recorded"


@dataclass
class BookUsageRecorder:
    root: Path
    ledger: UsageLedger

    def record(self, today: date) -> list[str]:
        """One line per timing file newly recorded or refused; files already in the ledger print nothing."""
        lines = []
        for path in sorted((self.root / AI_FOLDER).glob(TIMING_GLOB)):
            name = path.relative_to(self.root).as_posix()
            try:
                results = self._record(path, today)
            except (ExportRefused, UsageRefused, ValueError) as refused:
                results = [f"refused: {refused}"]
            lines += [LINE.format(file=name, result=result) for result in results if ALREADY not in result]
        return lines

    def _record(self, path: Path, today: date) -> list[str]:
        book, role = book_and_role(path.name)
        reader = SelfTimedUsageReader(path)
        return self.ledger.record(
            reader.days(), Attribution(PURPOSE_BOOKS_AND_ROLES, book, role), reader.complete_before(today)
        )


def book_and_role(name: str) -> tuple[str, str]:
    """`<day>_<book>.timing.json` is the book's forecast run (no role); `<day>_<book>_decision.timing.json` its trading
    decision run (story F1t)."""
    stem = name.removesuffix(".timing.json").split("_", 1)[-1]
    book = next((b for b in AI_BOOKS if stem == b or stem.startswith(f"{b}_")), "")
    run = stem.removeprefix(book).removeprefix("_") if book else ""
    if not book or run not in RUN_ROLES:
        raise ValueError(f"{stem!r} in the file name is not an AI book's run")
    return book, RUN_ROLES[run].format(book=book)
