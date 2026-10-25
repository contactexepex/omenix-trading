"""The point-in-time results table (story A12): each company's reported figures as they were known at a given moment,
read only from the archive (Drive), never from the exchange.

For each reporting period it returns the newest version of the filing made public at or before the moment asked
(`filed_at`); a filing made public later, and a revision made public later, are never returned. Both versions of a
revised filing stay in the archive (each is its own file and manifest row).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from ..constants import CONSOLIDATED, FILING_RESULTS
from ..storage.raw_store import RawFileStore, StoredCopyDamaged
from .manifest import ArchivedFiling, FilingManifest
from .results_parser import ResultFigures, parse_results


@dataclass(frozen=True)
class ResultRow:
    symbol: str
    consolidation: str
    filed_at: datetime
    url: str
    figures: ResultFigures


class ResultsTable:
    def __init__(self, manifest: FilingManifest, store: RawFileStore):
        self.manifest, self.store = manifest, store

    def as_of(self, symbol: str, moment: datetime, consolidation: str = CONSOLIDATED) -> list[ResultRow]:
        """One row per reporting period, oldest first: the newest version public at `moment` (timezone-aware)."""
        newest: dict = {}
        for row in self._known(symbol, consolidation, moment):
            newest[row.filing.period_end] = row  # rows come in filed_at order: a later version replaces an earlier
        return [self._read(row) for _, row in sorted(newest.items())]

    def _known(self, symbol: str, consolidation: str, moment: datetime) -> list[ArchivedFiling]:
        rows = (
            r
            for r in self.manifest.rows(FILING_RESULTS).values()
            if r.filing.symbol == symbol and r.filing.consolidation == consolidation and r.filing.filed_at <= moment
        )
        return sorted(rows, key=lambda r: r.filing.filed_at)

    def _read(self, row: ArchivedFiling) -> ResultRow:
        data = self.store.get(row.filing.path)
        if data is None or hashlib.sha256(data).hexdigest() != row.sha256:
            raise StoredCopyDamaged(f"{row.filing.path}: missing or not the manifest's SHA-256")
        f = row.filing
        return ResultRow(f.symbol, f.consolidation, f.filed_at, f.url, parse_results(data, f.period_end))
