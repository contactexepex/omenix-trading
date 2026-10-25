"""BANKNIFTY's derived close table in Drive (part A4): the latest receipted table file is read through the verified
Drive cache; an update reads the archived index-close files after the table's last day and writes a new
content-named file (write-once) when it found new closes."""

from __future__ import annotations

import hashlib
from datetime import date

from ..price_distribution.store import DistributionStore
from ..storage.drive_cache import DriveCache
from ..storage.receipts import ReceiptFolder
from .closes import TABLE_HEADER, IndexFileCloses, table_rows
from .folders import CLOSES, closes_path, drive

FIRST_DAY = date(2017, 1, 2)  # warmup_closes.csv's first session: the same history for both indices
UNVERIFIED = "the Drive cache could not verify the close tables: {problems}"
WRITTEN = "{underlying} closes: {n} new rows through {through}"
UNCHANGED = "{underlying} closes: no new row (table through {through})"


class CloseTables:
    def __init__(
        self, store: DistributionStore, receipts: ReceiptFolder, cache: DriveCache, first_day: date = FIRST_DAY
    ):
        self.store, self.receipts, self.cache, self.first_day = store, receipts, cache, first_day

    def latest_path(self, underlying: str) -> str | None:
        prefix = f"{underlying.lower()}_through_"
        paths = [r.path for r in self.receipts.under(drive(CLOSES)) if r.path.rsplit("/", 1)[-1].startswith(prefix)]
        return max(paths, default=None)  # ISO date, then zero-padded row count: the latest sorts last

    def latest_text(self, underlying: str) -> str | None:
        path = self.latest_path(underlying)
        if path is None:
            return None
        report = self.cache.sync(drive(CLOSES))
        if not report.complete:
            raise RuntimeError(UNVERIFIED.format(problems="; ".join(report.problems)))
        return self.cache.local(path).read_text(encoding="utf-8")

    def update(self, underlying: str, files: IndexFileCloses, through: date) -> list[str]:
        """Reads every regular session up to `through` that the table lacks, a late file's day included (a missing day
        is retried on every update, never skipped once a later day is found; review finding 3)."""
        text = self.latest_text(underlying)
        rows = {r.day: r for r in table_rows(text)} if text else {}
        names = dict(_names(text)) if text else {}
        wanted = [d for d in files.regular_sessions(self.first_day, through) if d not in rows]
        if not wanted:
            return [UNCHANGED.format(underlying=underlying, through=max(rows, default=None))]
        found, gaps = files.rows_for(underlying, wanted)
        if not found:
            return [*gaps, UNCHANGED.format(underlying=underlying, through=max(rows, default=None))]
        merged = {**{d: (d, r.value, names[d]) for d, r in rows.items()}, **{d: (d, v, n) for d, v, n in found}}
        lines = [f"{d.isoformat()},{v!r},{name}" for d, v, name in (merged[d] for d in sorted(merged))]
        data = (TABLE_HEADER + "\n" + "\n".join(lines) + "\n").encode()
        last = max(merged)
        self.store.put(closes_path(underlying, last, len(merged), hashlib.sha256(data).hexdigest()), data)
        return [*gaps, WRITTEN.format(underlying=underlying, n=len(found), through=last)]


def _names(text: str):
    for line in text.splitlines()[1:]:
        day, _, name = line.split(",", 2)
        yield date.fromisoformat(day), name
