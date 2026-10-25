"""Scoreboard B's adapters (story S2): the book's operating-cost file in C1's columns, the owner's overrides as D3
records them, the AI cost until F8 exists,
each day's marks from the execution snapshot E3 recorded, and the SHA-256 of every file the board reads."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from ..accounting.ledgers import read_operating_costs
from ..books.paths import account_folder, book_folder
from ..books.versions import VERSIONS_FILE
from ..constants import BOOK1_RULES, INDEX_NIFTY_50, JOURNAL_FOLDER
from ..desk.run_log import RUNS_FOLDER
from ..desk.snapshot import ContractKey, ExecutionSnapshot, ExecutionSnapshotSource
from ..market_read_models.nse_files import read_index_figures
from ..playbook.decision_store import DecisionStore
from ..scorecard.scorecard import snapshot_marks
from ..storage.raw_source import NseIndexCloseSource
from ..storage.raw_store import RawFileStore
from .committed_runs import DayRun
from .do_nothing import IndexDay

OPERATING_COSTS_FILE = "operating_costs.csv"


class FileOperatingCosts:
    """`journal/<book>/operating_costs.csv`, C1's columns; no file means none recorded."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, book: str) -> Path:
        return book_folder(self.root, book) / OPERATING_COSTS_FILE

    def rows(self, book: str) -> list[dict]:
        path = self.path(book)
        return read_operating_costs(path.read_text(encoding="utf-8")) if path.is_file() else []


class RecordedOwnerOverride:
    """D3's `owner_override` field, which F4 fills; empty (no override) until F4 exists."""

    def overridden(self, record: dict) -> bool:
        return bool(record.get("owner_override"))


class AiCostBeforeF8:
    """Book 1 runs no AI, so its allocated AI cost is a true zero; the AI books' cost is unknown until F8."""

    def allocated(self, book: str, first: date, last: date) -> float | None:
        return 0.0 if book == BOOK1_RULES else None


class SnapshotMarks:
    """A day's marks: the mid of every valid quote in the execution snapshot E3 recorded as valid that day; none on a
    day without one (the daily values then carry the last valid mark, flagged stale)."""

    def __init__(self, snapshots: ExecutionSnapshotSource, ids: Mapping[date, str]):
        self.snapshots, self.ids = snapshots, dict(ids)
        self._marks: dict[date, Mapping[ContractKey, float]] = {}

    def __call__(self, day: date) -> Mapping[ContractKey, float]:
        if day not in self.ids:
            return {}
        if day not in self._marks:
            self._marks[day] = snapshot_marks(self.snapshots.snapshot(day, self.ids[day]))
        return self._marks[day]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_hashes(root: Path, books: Sequence[str], runs: Sequence[DayRun]) -> dict[str, str]:
    """Every record file the board reads, by repository path (dot files and temporary files aside); the quote
    snapshots are named by the run logs, which are hashed here."""
    root = Path(root)
    folders = [root / JOURNAL_FOLDER / RUNS_FOLDER, *(account_folder(root, b) for b in books)]
    folders += [DecisionStore(root, r.book).day_folder(r.day) / r.run_id for r in runs]
    paths = [p for folder in folders if folder.is_dir() for p in folder.iterdir() if p.is_file()]
    paths += [root / VERSIONS_FILE, *(book_folder(root, b) / OPERATING_COSTS_FILE for b in books)]
    kept = sorted({p for p in paths if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".tmp")})
    return {p.relative_to(root).as_posix(): _sha256(p) for p in kept}


class NoMatchedShadowYet:
    """F7 is not built: Book 3 has no matched shadow decisions, so every Book 3 day on scoreboard A is "F7 not
    built"."""

    def records(self, day: date) -> list[dict] | None:
        return None


class DaySnapshots:
    """Each day's valid execution snapshot, the one E3's run log names (story S3); None on a day without one. A named
    capture that cannot be read raises: the board never values a unit on a guessed price."""

    def __init__(self, snapshots: ExecutionSnapshotSource, ids: Mapping[date, str]):
        self.snapshots, self.ids = snapshots, dict(ids)
        self._read: dict[date, ExecutionSnapshot] = {}

    def __call__(self, day: date) -> ExecutionSnapshot | None:
        if day not in self.ids:
            return None
        if day not in self._read:
            self._read[day] = self.snapshots.snapshot(day, self.ids[day])
        return self._read[day]


class ArchivedIndexLevels:
    """The NIFTY 50 close and dividend yield of a session, from NSE's index-close file as archived (A13's source,
    `read_index_figures`), never fetched here; None when the day's file is not archived (story S6: never filled)."""

    def __init__(self, raw: RawFileStore | None):
        self.raw = raw
        self._days: dict[date, IndexDay | None] = {}

    def __call__(self, day: date) -> IndexDay | None:
        if day not in self._days:
            data = self.raw.get(NseIndexCloseSource.path_for(day)) if self.raw else None
            figures = read_index_figures(data, NseIndexCloseSource.filename_for(day)) if data else {}
            nifty = figures.get(INDEX_NIFTY_50)
            self._days[day] = IndexDay(nifty.close, nifty.dividend_yield) if nifty else None
        return self._days[day]
