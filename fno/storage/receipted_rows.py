"""O9b's receipt-backed tables (story O9b, section 2): an append-only table as a series of write-once Drive parts, and a
report rewritten every run as a series of snapshots, both written through O9's `DataStore` (one SHA-256 receipt per
file) and read through the verified `DriveCache` (the receipts are the index; Drive is never listed, and a missing or
changed file stops the reader). Parts are named by the writing run's id, which sorts by time, so a table's rows are
its parts' rows in name order; a table moved from the repository starts with today's file as its first part, so the
rebuilt table equals the old file byte for byte."""

from __future__ import annotations

import csv
import io

from .data_store import DataStore
from .drive_cache import DriveCache
from .report_files import Report
from .row_log import RowLog

PART = "{folder}/{run_id}{n}.csv"  # one part per run; a second write in the same run gets "_02" (sorts after ".csv")
TABLE_UNREADABLE = "{folder}: the Drive copies could not be verified: {problems}"


class DriveDataUnavailable(RuntimeError):
    """A receipted file was missing from Drive or held other bytes: nothing of the table is read."""


class _ReceiptedSeries:
    def __init__(self, store: DataStore, cache: DriveCache, folder: str):
        """`folder`: inside the store's area (e.g. `vix/india_vix_daily`)."""
        self.store, self.cache, self.folder = store, cache, folder
        self._writes = 0

    def write_bytes(self, data: bytes) -> None:
        """One new write-once file of this run (the move of an existing file uses it for the first part)."""
        self._writes += 1
        n = "" if self._writes == 1 else f"_{self._writes:02d}"
        self.store.put(PART.format(folder=self.folder, run_id=self.store.run_id, n=n), data)

    def files(self) -> list[bytes]:
        """Every receipted file of the series, verified, in name order."""
        prefix = f"{self.store.area}/{self.folder}"
        if not self.cache.receipts.under(prefix):
            return []  # a series with nothing written yet is empty, not unreadable
        report = self.cache.sync(prefix)
        if not report.complete:
            raise DriveDataUnavailable(TABLE_UNREADABLE.format(folder=prefix, problems="; ".join(report.problems)))
        return [self.cache.local(r.path).read_bytes() for r in self.cache.receipts.under(prefix)]


class ReceiptedRowLog(_ReceiptedSeries, RowLog):
    def rows(self) -> list[dict[str, str]]:
        return list(csv.DictReader(self.rebuilt().decode("utf-8").splitlines()))

    def rebuilt(self) -> bytes:
        """The table as one CSV: the first part whole, then each later part without its header line."""
        parts = self.files()
        return b"".join([parts[0], *(part.split(b"\n", 1)[1] for part in parts[1:])]) if parts else b""

    def current_bytes(self) -> bytes:
        return self.rebuilt()

    def check_appendable(self) -> None:
        """Every append is a new write-once part: nothing existing can change."""

    def append(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        if rows:
            self.write_bytes(_csv(fields, rows))


class ReceiptedSnapshots(_ReceiptedSeries, Report):
    """A report rewritten every run: one new file per run, the newest is current (as A17's `DriveSnapshots`)."""

    def write(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        self.write_bytes(_csv(fields, rows))

    def latest_bytes(self) -> bytes | None:
        files = self.files()
        return files[-1] if files else None

    def current_bytes(self) -> bytes:
        return self.latest_bytes() or b""

    def latest(self) -> list[dict[str, str]]:
        data = self.latest_bytes()
        return list(csv.DictReader(data.decode("utf-8").splitlines())) if data else []


def _csv(fields: tuple[str, ...], rows: list[tuple]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")
