"""Receipts rebuilt from Drive (story RR1): for every Drive file under a prefix that has no receipt, write the per-file
SHA-256 receipt its CURRENT bytes prove.

**What the rebuilt receipt proves, and what it does not.** It proves the file's bytes AS OF THE REBUILD (owner's
accepted caveat, 27 Oct 2026): from now on a change to the file is detected. It does NOT prove the file is what the
original run wrote, and its time is the rebuild's, not the original write's (its writer is `rebuild-receipts`, so it
is visible as a rebuild). It is for the case where the receipts were never moved into this repository but the files
are in Drive.

**It only adds.** An existing receipt is never replaced: when the file still matches it, the file is counted as
already receipted; when it does NOT match, that is reported as a problem (a file changed behind its receipt) and left
alone. Report only unless `apply`. It reads Drive and writes only `receipts/`; it changes nothing in Drive."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fno.ingestion.storage.raw_store import RawFileStore
from fno.ingestion.storage.receipts import Receipt, ReceiptFolder
from fno.shared.models import now_utc

WRITER = "rebuild-receipts"
FILES, ALREADY, WRITTEN, WOULD_WRITE, DIFFERS, UNREADABLE = (
    "files", "already_receipted", "written", "would_write", "differs_from_receipt", "unreadable")  # fmt: skip
KEYS = (FILES, ALREADY, WOULD_WRITE, WRITTEN, DIFFERS, UNREADABLE)
DIFFERS_MESSAGE = "{path}: the Drive file no longer matches its receipt; the receipt is kept, nothing is changed"
UNREADABLE_MESSAGE = "{path}: could not be read from Drive ({kind}); no receipt written"


@dataclass
class RebuildReport:
    counts: Counter = field(default_factory=Counter)
    problems: list[str] = field(default_factory=list)
    apply: bool = False

    @property
    def ok(self) -> bool:
        return not self.problems

    def line(self) -> str:
        mode = "applied" if self.apply else "report only"
        return f"rebuild receipts ({mode}): " + ", ".join(f"{key} {self.counts[key]}" for key in KEYS)


class ReceiptRebuild:
    def __init__(self, drive: RawFileStore, receipts: ReceiptFolder, run_id: str,
                 clock: Callable[[], datetime] = now_utc):  # fmt: skip
        """`drive`: the project folder, read only here; `receipts`: the checkout's receipts, the only thing written."""
        self.drive, self.receipts, self.run_id, self.clock = drive, receipts, run_id, clock

    def run(self, prefixes: Sequence[str], apply: bool) -> RebuildReport:
        report = RebuildReport(apply=apply)
        for prefix in prefixes:
            self._walk(prefix, apply, report)
        return report

    def _walk(self, folder: str, apply: bool, report: RebuildReport) -> None:
        for name in sorted(self.drive.checksums(folder)):
            if not name.startswith("."):  # dot-files are partial writes, not data
                self._file(f"{folder}/{name}", apply, report)
        for child in self.drive.folders(folder):
            self._walk(f"{folder}/{child}", apply, report)

    def _file(self, path: str, apply: bool, report: RebuildReport) -> None:
        report.counts[FILES] += 1
        try:
            data = self.drive.get(path)
        except Exception as error:  # noqa: BLE001 - Drive errors may name paths; only the class is kept
            data = None
            kind = type(error).__name__
        else:
            kind = "absent"
        if data is None:
            report.counts[UNREADABLE] += 1
            report.problems.append(UNREADABLE_MESSAGE.format(path=path, kind=kind))
            return
        digest = hashlib.sha256(data).hexdigest()
        existing = self.receipts.read(path)
        if existing is not None:
            if existing.sha256 == digest:
                report.counts[ALREADY] += 1
            else:
                report.counts[DIFFERS] += 1
                report.problems.append(DIFFERS_MESSAGE.format(path=path))
            return
        if not apply:
            report.counts[WOULD_WRITE] += 1
            return
        self.receipts.write(
            Receipt(path, digest, len(data), self.clock().astimezone(UTC).isoformat(), WRITER, self.run_id)
        )
        report.counts[WRITTEN] += 1
