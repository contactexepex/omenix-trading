"""Story R2: receipts packed one file per run (the news writers). Each line is the receipt of one Drive file: the same
fields a per-file receipt holds plus the Drive path, so a batch proves every file it lists on its own, and a reader
finds a file's proof by its path. Run ids are unique, so two runs never touch one batch file (no merge conflicts, the
property the one-file-per-receipt layout was chosen for).

Write-once as for per-file receipts: the same digest again keeps the first line, a different digest for a path that
already has a receipt (in any batch or in a per-file receipt) is refused, and nothing in the code edits or removes a
line.

A damaged line is NEVER read as a receipt and NEVER a crash: it is reported as a `BatchProblem`. A problem that names a
file (a torn or malformed line whose path is readable, or two digests for one path) makes a sync of a prefix that covers
that file incomplete, until the file has a valid receipt (a torn line is settled by the next run saving the file again).
A problem that names no file proves nothing about any file and is a warning; both are shown only to syncs of the
batched areas, so news damage never reaches an unrelated table (flows, circulars, pre-open)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from fno.ingestion.storage.raw_store import RawFileConflict, path_parts
from fno.ingestion.storage.receipt import FIELD_SEPARATOR, Receipt

if TYPE_CHECKING:
    from fno.ingestion.storage.receipts import ReceiptFolder

BATCH_FOLDER = "_batches"  # receipts/_batches/<YYYY>/<MM>/<run id>.tsv: one small folder a month, never one huge one
BATCH_SUFFIX = ".tsv"
BATCHED_AREAS = ("raw/news",)  # the Drive areas whose receipts are packed in batches (a new user adds its area here)
FIELDS = 6  # path, sha256, size, written_at, writer, run_id
HEX64 = re.compile(r"[0-9a-f]{64}")
BAD_RUN_ID = "a batch run id starts with its UTC date (YYYYMMDD): {run_id!r}"
BAD_PATH = "a receipt path must be a valid archive path without tabs or line breaks"
UNREADABLE = "{file}: cannot be read as text; none of its lines is read as a receipt"
TORN = "{file}: last line has no line break (a write cut short); not read as a receipt"
MALFORMED = "{file} line {number}: not a whole receipt line; not read as a receipt"
UNPROVED = "{path}: its receipt line in {file} is cut short or malformed, so the file is not proved"
CONFLICT = "{file} line {number}: a different digest than the first receipt for the same path; the first is kept"
PER_FILE_CONFLICT = "{path}: the batch and the per-file receipt hold different digests; the per-file one is read"
NOT_AT_LINE_END = "{file} does not end in a line break (an earlier write was cut short); nothing more is appended to it"
SHORT_WRITE = "{file}: the receipt line was not written whole"


def cut_torn_tails(folder: Path) -> list[Path]:
    """Cuts the half line off the end of every batch file under `folder` that does not end in a line break, and returns
    the files cut. Only a fragment that was never a whole receipt line is removed (it was never read as a receipt); no
    whole line is ever touched. The commit step of the news workflows runs it so a killed run never publishes a torn
    line to `main`."""
    cut = []
    for file in sorted(Path(folder).rglob(f"*{BATCH_SUFFIX}")) if Path(folder).is_dir() else []:
        data = file.read_bytes()
        if data and not data.endswith(b"\n"):
            file.write_bytes(data[: data.rfind(b"\n") + 1])
            cut.append(file)
    return cut


class BatchBroken(OSError):
    """A batch file cannot take the next line whole; the file is not changed, the run ends red."""


@dataclass(frozen=True)
class BatchProblem:
    message: str
    path: str | None = None  # the Drive file the problem is about, when its path could be read
    settled_by_a_receipt: bool = False  # a torn or malformed line stops mattering once the path has a valid receipt


def batch_file_name(run_id: str) -> str:
    """`<YYYY>/<MM>/<run id>.tsv`, the month taken from the run id (`new_run_id` starts with its UTC date)."""
    if len(run_id) < 8 or not run_id[:8].isdigit() or not 1 <= int(run_id[4:6]) <= 12:
        raise ValueError(BAD_RUN_ID.format(run_id=run_id))
    return f"{run_id[:4]}/{run_id[4:6]}/{run_id}{BATCH_SUFFIX}"


def batch_line(receipt: Receipt) -> str:
    return FIELD_SEPARATOR.join((receipt.path, *receipt.to_text().rstrip("\n").split(FIELD_SEPARATOR))) + "\n"


def _readable_path(text: str) -> str | None:
    try:
        path_parts(text)
    except ValueError:
        return None
    return None if "\r" in text else text


def _receipt_of(fields: list[str]) -> Receipt | None:
    """The receipt a whole line holds, or None for anything else (wrong field count, a digest that is not 64 hex
    characters, a size that is not a number, an unusable path, a carriage return in any field)."""
    if len(fields) != FIELDS or any("\r" in f for f in fields):
        return None
    path, sha256, size, written_at, writer, run_id = fields
    if _readable_path(path) is None or not HEX64.fullmatch(sha256) or not size.isdigit():
        return None
    return Receipt(path, sha256, int(size), written_at, writer, run_id)


def _attributed(text: str) -> str | None:
    """The path a damaged line was about, when readable and inside a batched area (else the line names no file)."""
    path = _readable_path(text)
    if path is None:
        return None
    parts = path_parts(path)
    return path if any(parts[: len(area)] == area for area in map(path_parts, BATCHED_AREAS)) else None


def covers(prefix: str, path: str | None) -> bool:
    """Whether a sync of `prefix` should see a problem: one that names a file, if the prefix covers the file; one that
    names none, if the prefix is inside or around a batched area."""
    wanted = path_parts(prefix)
    if path is not None:
        return path_parts(path)[: len(wanted)] == wanted
    areas = map(path_parts, BATCHED_AREAS)
    return any(area[: len(wanted)] == wanted or wanted[: len(area)] == area for area in areas)


class BatchIndex:
    """Every receipt in the batch folder, by Drive path, loaded when first asked and kept current by the writer."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self._receipts: dict[str, Receipt] | None = None
        self._problems: list[BatchProblem] = []

    def receipts(self) -> dict[str, Receipt]:
        if self._receipts is None:
            self._receipts = {}
            for file in sorted(self.folder.rglob(f"*{BATCH_SUFFIX}")) if self.folder.is_dir() else []:
                self._load(file)
        return self._receipts

    def problems(self) -> list[BatchProblem]:
        known = self.receipts()
        return [p for p in self._problems if not (p.settled_by_a_receipt and p.path in known)]

    def add(self, receipt: Receipt) -> None:
        self.receipts().setdefault(receipt.path, receipt)

    def _load(self, file: Path) -> None:
        try:
            text = file.read_bytes().decode("utf-8")  # exact bytes: no newline translation
        except (OSError, UnicodeDecodeError):
            self._problems.append(BatchProblem(UNREADABLE.format(file=file.name)))
            return
        *lines, tail = text.split("\n")  # the tail is "" when the file ends with a line break
        for number, line in enumerate(lines, start=1):
            self._line(file, number, line)
        if tail:
            path = _attributed(tail.split(FIELD_SEPARATOR)[0]) if FIELD_SEPARATOR in tail else None
            self._problems.append(BatchProblem(TORN.format(file=file.name), None))
            if path:  # the file the cut-off line was about is named, so a verifier reports it as unproved
                self._problems.append(BatchProblem(UNPROVED.format(path=path, file=file.name), path, True))

    def _line(self, file: Path, number: int, line: str) -> None:
        fields = line.split(FIELD_SEPARATOR)
        receipt = _receipt_of(fields)
        if receipt is None:
            path = _attributed(fields[0]) if len(fields) > 1 else None
            message = (
                UNPROVED.format(path=path, file=file.name) if path else MALFORMED.format(file=file.name, number=number)
            )
            self._problems.append(BatchProblem(message, path, True))
            return
        kept = self._receipts.setdefault(receipt.path, receipt)
        if kept.sha256 != receipt.sha256:
            self._problems.append(BatchProblem(CONFLICT.format(file=file.name, number=number), receipt.path))


class BatchReceiptWriter:
    """Writes each receipt as one line of its run's batch file (`<folder>/_batches/<YYYY>/<MM>/<run id>.tsv`)."""

    def __init__(self, receipts: ReceiptFolder, run_id: str):
        """`run_id`: the run whose batch file this is, checked now, before the run writes anything to Drive."""
        self.receipts, self.file_name = receipts, batch_file_name(run_id)

    def write(self, receipt: Receipt) -> Receipt:
        """The receipt kept for the path: the earlier one when the digest matches, else the new one."""
        if _readable_path(receipt.path) is None or FIELD_SEPARATOR in receipt.path or "\n" in receipt.path:
            raise ValueError(BAD_PATH)
        existing = self.receipts.read(receipt.path)
        if existing is not None:
            if existing.sha256 != receipt.sha256:
                raise RawFileConflict(f"{receipt.path} already has a receipt with a different SHA-256")
            return existing
        self._append(self.receipts.folder / BATCH_FOLDER / self.file_name, batch_line(receipt).encode("utf-8"))
        self.receipts.batches.add(receipt)
        return receipt

    @staticmethod
    def _append(file: Path, line: bytes) -> None:
        """The whole line or an error: never glued onto a half line, and a half line left by a failed write makes the
        next append refuse (a lost receipt would be a Record file nothing proves)."""
        file.parent.mkdir(parents=True, exist_ok=True)
        if file.exists() and file.stat().st_size and file.read_bytes()[-1:] != b"\n":
            raise BatchBroken(NOT_AT_LINE_END.format(file=file.name))
        descriptor = os.open(file, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            rest = memoryview(line)
            while rest:
                written = os.write(descriptor, rest)
                if written <= 0:
                    raise BatchBroken(SHORT_WRITE.format(file=file.name))
                rest = rest[written:]
        finally:
            os.close(descriptor)
