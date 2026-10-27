"""Story R2: receipts packed one file per run (the news writers). Each line is the receipt of one Drive file: the same
fields a per-file receipt holds plus the Drive path, so a batch proves every file it lists on its own, and a reader
finds a file's proof by its path. Run ids are unique, so two runs never touch one batch file (no merge conflicts, the
property the one-file-per-receipt layout was chosen for).

Write-once as for per-file receipts: the same digest again keeps the first line, a different digest for a path that
already has a receipt (in any batch or in a per-file receipt) is refused, and nothing in the code edits or removes a
line. A last line without its newline (a write cut short) is never read as a receipt; it is reported."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from fno.ingestion.storage.raw_store import RawFileConflict
from fno.ingestion.storage.receipt import FIELD_SEPARATOR, Receipt

if TYPE_CHECKING:
    from fno.ingestion.storage.receipts import ReceiptFolder

BATCH_FOLDER = "_batches"  # receipts/_batches/<YYYY>/<MM>/<run id>.tsv: one small folder a month, never one huge one
BATCH_SUFFIX = ".tsv"
FIELDS = 6  # path, sha256, size, written_at, writer, run_id
BAD_RUN_ID = "a batch run id starts with its UTC date (YYYYMMDD): {run_id!r}"
BAD_PATH = "a receipt path must be non-empty without tabs or line breaks"
TORN = "{file}: last line has no line break (a write cut short); not read as a receipt"
UNPROVED = "{path}: its receipt line is cut short, so the file is not proved"
MALFORMED = "{file} line {number}: not {fields} fields; not read as a receipt"
CONFLICT = "{file} line {number}: a different digest than the first receipt for the same path; the first is kept"


def batch_file_name(run_id: str) -> str:
    """`<YYYY>/<MM>/<run id>.tsv`, the month taken from the run id (`new_run_id` starts with its UTC date)."""
    if len(run_id) < 8 or not run_id[:8].isdigit() or not 1 <= int(run_id[4:6]) <= 12:
        raise ValueError(BAD_RUN_ID.format(run_id=run_id))
    return f"{run_id[:4]}/{run_id[4:6]}/{run_id}{BATCH_SUFFIX}"


def batch_line(receipt: Receipt) -> str:
    return FIELD_SEPARATOR.join((receipt.path, *receipt.to_text().rstrip("\n").split(FIELD_SEPARATOR))) + "\n"


class BatchIndex:
    """Every receipt in the batch folder, by Drive path, loaded when first asked and kept current by the writer."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self._receipts: dict[str, Receipt] | None = None
        self.problems: list[str] = []

    def receipts(self) -> dict[str, Receipt]:
        if self._receipts is None:
            self._receipts = {}
            for file in sorted(self.folder.rglob(f"*{BATCH_SUFFIX}")) if self.folder.is_dir() else []:
                self._load(file)
        return self._receipts

    def add(self, receipt: Receipt) -> None:
        self.receipts().setdefault(receipt.path, receipt)

    def _load(self, file: Path) -> None:
        text = file.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        for number, line in enumerate(lines, start=1):
            if not line.endswith("\n"):
                self.problems.append(TORN.format(file=file.name))
                path = line.split(FIELD_SEPARATOR)[0] if FIELD_SEPARATOR in line else ""
                if path:  # the file this line was about is named, so a verifier reports it as unproved
                    self.problems.append(UNPROVED.format(path=path))
                continue
            fields = line.rstrip("\n").split(FIELD_SEPARATOR)
            if len(fields) != FIELDS:
                self.problems.append(MALFORMED.format(file=file.name, number=number, fields=FIELDS))
                continue
            path, sha256, size, written_at, writer, run_id = fields
            receipt = Receipt(path, sha256, int(size), written_at, writer, run_id)
            kept = self._receipts.setdefault(path, receipt)
            if kept.sha256 != receipt.sha256:
                self.problems.append(CONFLICT.format(file=file.name, number=number))


class BatchReceiptWriter:
    """Writes each receipt as one line of its run's batch file (`<folder>/_batches/<run id>.tsv`)."""

    def __init__(self, receipts: ReceiptFolder, run_id: str):
        """`run_id`: the run whose batch file this is, checked now, before the run writes anything to Drive."""
        self.receipts, self.file_name = receipts, batch_file_name(run_id)

    def write(self, receipt: Receipt) -> Receipt:
        """The receipt kept for the path: the earlier one when the digest matches, else the new one."""
        if not receipt.path or any(c in receipt.path for c in ("\t", "\n", "\r")):
            raise ValueError(BAD_PATH)
        existing = self.receipts.read(receipt.path)
        if existing is not None:
            if existing.sha256 != receipt.sha256:
                raise RawFileConflict(f"{receipt.path} already has a receipt with a different SHA-256")
            return existing
        file = self.receipts.folder / BATCH_FOLDER / self.file_name
        file.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(file, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(descriptor, batch_line(receipt).encode("utf-8"))  # the whole line in one write
        finally:
            os.close(descriptor)
        self.receipts.batches.add(receipt)
        return receipt
