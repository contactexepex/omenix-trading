"""Archiving a practice file (story MS-SIM-e, 7.8): write-once to Drive, then its receipt pushed, through the same two
steps as the pilot's dashcam seal (O9's `DataStore`, the receipt publisher). Nothing here is a new mechanism: the three
collaborators are handed in by their protocols.

Rules, each tested: a stored line without the practice label is refused; the same bytes again return the same archived
file and make no second commit; other bytes for an existing key are refused as "rule broken" and nothing is written;
the file is read back from Drive and its SHA-256 compared with its receipt before the run counts as archived."""

import gzip
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ....storage.raw_store import RawFileConflict
from ...contracts.codec import from_plain
from ...contracts.slot_file import RECORD_TYPES
from ..constants import PRACTICE_LABEL
from .names import checked, run_folder

RULE_BROKEN = "rule broken: {path} is archived with other bytes; an archived practice file is never overwritten"
UNLABELLED = "{path}: line {line} does not carry the practice label"
NOT_RECORDS = "{path}: not gzip canonical record lines"
NOT_TEXT = "{path}: not UTF-8 text"
OUTSIDE = "{path} is not in the run {run}"
DAMAGED = "{path} read back from Drive holds other bytes than its receipt"
RECORD_SUFFIX = ".jsonl.gz"
TEXT_SUFFIX = ".txt"


class PracticeArchiveError(Exception):
    """A practice file the archive refuses; nothing was written."""


class UnlabelledFile(PracticeArchiveError):
    pass


class PracticeConflict(PracticeArchiveError):
    pass


class ArchiveDamaged(PracticeArchiveError):
    pass


class Receipt(Protocol):
    path: str
    sha256: str


class PushedReceipt(Protocol):
    commit: str
    pushed_at: datetime
    sha256: str


class DataPort(Protocol):
    area: str

    def put(self, path: str, data: bytes) -> Receipt: ...


class PublisherPort(Protocol):
    def publish(self, drive_path: str, what: str) -> PushedReceipt: ...

    def published(self, drive_path: str) -> PushedReceipt | None: ...


class ReaderPort(Protocol):
    def read(self, path: str) -> bytes: ...


@dataclass(frozen=True)
class ArchivedFile:
    path: str  # under the data area, e.g. `school-practice/<run id>/median/2024/03/04/1500.decisions.jsonl.gz`
    sha256: str
    commit: str
    pushed_at: datetime


def check_labelled(path: str, data: bytes) -> None:
    """Every stored line carries `practice (simulator)`: in the line's `label` key for a record file, at its start for
    text. A record line must also decode as the pilot's `decode_slot_file` decodes it (a known `type`, a `record` that
    builds); a file that is neither canonical record lines nor labelled text is refused."""
    if path.endswith(RECORD_SUFFIX):
        for number, line in enumerate(_lines(path, data), start=1):
            row = _row(path, line)
            if row.get("label") != PRACTICE_LABEL:
                raise UnlabelledFile(UNLABELLED.format(path=path, line=number))
            _decoded(path, row)
    elif path.endswith(TEXT_SUFFIX):
        for number, line in enumerate(_text(path, data).splitlines(), start=1):
            if line and not line.startswith(PRACTICE_LABEL):
                raise UnlabelledFile(UNLABELLED.format(path=path, line=number))
    else:
        raise PracticeArchiveError(NOT_RECORDS.format(path=path))


def _text(path: str, data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PracticeArchiveError(NOT_TEXT.format(path=path)) from error


def _row(path: str, line: bytes) -> dict:
    try:
        row = json.loads(line)
    except ValueError as error:
        raise PracticeArchiveError(NOT_RECORDS.format(path=path)) from error
    if not isinstance(row, dict):
        raise PracticeArchiveError(NOT_RECORDS.format(path=path))
    return row


def _decoded(path: str, row: dict) -> None:
    try:
        from_plain(RECORD_TYPES[row["type"]], row["record"])
    except Exception as error:  # noqa: BLE001 - any record that does not build is refused by name
        raise PracticeArchiveError(NOT_RECORDS.format(path=path)) from error


def _lines(path: str, data: bytes) -> list[bytes]:
    """The record lines of a gzip file; a slot with nothing to record (no closed trade) is an empty file, as the fleet
    writes it, and holds no line to label."""
    if not data:  # gzip.decompress(b"") is b"": a file with no gzip member at all is not an empty record file
        raise PracticeArchiveError(NOT_RECORDS.format(path=path))
    try:
        return [line for line in gzip.decompress(data).splitlines() if line]
    except (OSError, EOFError) as error:
        raise PracticeArchiveError(NOT_RECORDS.format(path=path)) from error


def _inside(run: str, path: str) -> bool:
    """In the run's folder, with no empty or climbing part (DataStore refuses these too; the archive says so first)."""
    folder = run_folder(checked(run)) + "/"
    parts = path.split("/")
    return path.startswith(folder) and all(part not in ("", "..", ".") for part in parts)


class PracticeArchive:
    def __init__(self, data: DataPort, publisher: PublisherPort, reader: ReaderPort):
        self.data, self.publisher, self.reader = data, publisher, reader

    def archive(self, run: str, path: str, payload: bytes, what: str) -> ArchivedFile:
        """`path` is a practice path of `run` (see `names.file_path`). Returns the archived file; a rerun with the same
        bytes returns the same one without a second commit."""
        if not _inside(run, path):
            raise PracticeArchiveError(OUTSIDE.format(path=path, run=run))
        check_labelled(path, payload)
        digest = hashlib.sha256(payload).hexdigest()
        existing = self.publisher.published(f"{self.data.area}/{path}")  # judged on the remote's receipt
        if existing is not None:
            if existing.sha256 != digest:
                raise PracticeConflict(RULE_BROKEN.format(path=path))
            return ArchivedFile(path, digest, existing.commit, existing.pushed_at)
        try:
            receipt = self.data.put(path, payload)
        except RawFileConflict as conflict:
            raise PracticeConflict(RULE_BROKEN.format(path=path)) from conflict
        pushed = self.publisher.publish(receipt.path, what)
        return ArchivedFile(path, receipt.sha256, pushed.commit, pushed.pushed_at)

    def verify(self, archived: ArchivedFile) -> None:
        """Reads the file back from Drive; `ArchiveDamaged` unless it holds the receipt's bytes."""
        data = self.reader.read(archived.path)
        if hashlib.sha256(data).hexdigest() != archived.sha256:
            raise ArchiveDamaged(DAMAGED.format(path=archived.path))
