"""What protocol v4's 15:10 deadline checks (story G10 completion, criterion 7): every live commitment a forecaster
makes itself on a day, (i) each live row of the CSV records in G8's folder (G7's rules, M1's weather) and (ii) each
receipt of a Drive-stored live record (G7b's V4 and V5, `receipts/data/v4/records/live/`). The AI books are left out
by their own set: their commitment is their sealed submission, checked by G11's timing (never `PACK_READERS`, which
also holds G7b's pack-reading forecasters).

Limit, said plainly (judge 584 m3): the rows and receipts are read from this run's checkout when the check runs (15:12
or later). Every G7, M1 and G7b live record is written and committed by the daily run's own checkout, so the check sees
them all. A forecaster committing from another session must have its commit in this checkout by then, or G8 counts its
row late (a row the day's verdict file does not name); G7b and G11 keep their v4 rows in the daily run's checkout, or
this check first reads `origin/main` (a later change)."""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import BOOK2_HYBRID, BOOK3_AI
from .commitment import CommitmentTimeUnknown

SEALED_COMMITMENTS = frozenset({BOOK2_HYBRID, BOOK3_AI})  # committed by a sealed submission, not by a record
LIVE = "live"  # G7's label of a live row
ROW, FILE = "row", "file"
UNREADABLE = "{path} line {number}: not one record row ({found} fields for {expected} columns)"


class CommitmentsUnreadable(CommitmentTimeUnknown):
    """A record file line that is not one row: no time can be established for it, so the day is not checked."""


@dataclass(frozen=True)
class Commitment:
    forecaster: str
    question: str
    kind: str  # ROW: `text` is the record's CSV line in `path`; FILE: `path` is the receipt the commit added
    path: str  # repository path
    text: str = ""


class CommitmentSource(ABC):
    @abstractmethod
    def commitments(self, day: date) -> list[Commitment]:
        """The day's live commitments to check, in a fixed order."""


class RecordCommitments(CommitmentSource):
    def __init__(self, root: Path, records: str, live_receipts: str):
        """`records`: G8's folder of CSV records; `live_receipts`: the receipts folder of Drive-stored live records,
        both repository paths."""
        self.root, self.records, self.live_receipts = Path(root), records, live_receipts

    def commitments(self, day: date) -> list[Commitment]:
        return [*self._rows(day), *self._files(day)]

    def _rows(self, day: date) -> list[Commitment]:
        found = []
        for file in sorted((self.root / self.records).glob("*/*.csv")):
            forecaster, question = file.parent.name, file.stem
            if forecaster in SEALED_COMMITMENTS:
                continue
            lines = file.read_text(encoding="utf-8").splitlines()
            header = next(csv.reader(lines[:1]), [])
            for number, line in enumerate(lines[1:], 2):
                row = self._row(header, line, file, number)
                if row.get("day") == day.isoformat() and row.get("label") == LIVE:
                    found.append(Commitment(forecaster, question, ROW, self._relative(file), line))
        return found

    def _row(self, header: list[str], line: str, file: Path, number: int) -> dict[str, str]:
        """One CSV line as its row (its own text is what git's pickaxe finds); a blank line is no row."""
        if not line.strip():
            return {}
        values = next(csv.reader([line]))
        if len(values) != len(header):
            raise CommitmentsUnreadable(UNREADABLE.format(path=self._relative(file), number=number,
                                                          found=len(values), expected=len(header)))  # fmt: skip
        return dict(zip(header, values, strict=True))

    def _files(self, day: date) -> list[Commitment]:
        pattern = f"*/*/{day:%Y}/{day.isoformat()}.json.sha256"
        receipts = sorted((self.root / self.live_receipts).glob(pattern))
        return [Commitment(r.parent.parent.parent.name, r.parent.parent.name, FILE, self._relative(r))
                for r in receipts if r.parent.parent.parent.name not in SEALED_COMMITMENTS]  # fmt: skip

    def _relative(self, file: Path) -> str:
        return file.relative_to(self.root).as_posix()
