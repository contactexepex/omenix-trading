"""Saves one filing's XBRL file into the raw archive and writes its manifest row in the same operation (story A12).

A file is saved only once it reads as XBRL (an error page or a cut-off download never enters the archive). For a
results file the manifest also says whether it holds a balance sheet and a cash-flow statement, read by the same
parser research uses, so the half-year check (A12 criterion 6) needs no second download.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date, datetime

from ..constants import FILING_RESULTS
from ..storage.raw_store import RawFileStore
from .filing import Filing
from .manifest import ArchivedFiling, FilingManifest
from .results_parser import parse_results
from .xbrl import read_facts


class FilingArchive:
    def __init__(self, store: RawFileStore, manifest: FilingManifest, clock: Callable[[], datetime]):
        self.store, self.manifest, self.clock = store, manifest, clock

    def has(self, filing: Filing) -> bool:
        """Whether the manifest already has the file (it is then in the archive: rows follow saves)."""
        return filing.url in self.manifest.rows(filing.kind)

    def has_any(self, symbol: str, kind: str, since: date) -> bool:
        """Whether the archive holds any file of that type for the company made public on or after `since`."""
        rows = self.manifest.rows(kind).values()
        return any(r.filing.symbol == symbol and r.filing.filed_at.date() >= since for r in rows)

    def save(self, filing: Filing, data: bytes) -> ArchivedFiling:
        """Checks, saves and fingerprints the file; NotXbrl (a ValueError) when it is not XBRL, nothing saved."""
        balance_sheet = cash_flow = None
        if filing.kind == FILING_RESULTS:
            figures = parse_results(data, filing.period_end)
            balance_sheet, cash_flow = figures.has_balance_sheet, figures.has_cash_flow
        else:
            read_facts(data)  # checks it is XBRL
        self.store.put(filing.path, data)
        row = ArchivedFiling(
            filing,
            self.clock(),
            hashlib.sha256(data).hexdigest(),
            hashlib.md5(data).hexdigest(),  # noqa: S324 - matches Drive's own checksum, not security
            len(data),
            balance_sheet,
            cash_flow,
        )
        self.manifest.record(row)
        return row
