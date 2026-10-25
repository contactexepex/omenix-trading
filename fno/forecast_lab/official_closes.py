"""NSE's official closes for the morning edition (story FL1-1d-2). G13b's close tables are updated by later jobs (the
NIFTY warm-up table at 21:11 or later, BANKNIFTY's table in the 14:33 run), so at 08:50 they rarely hold the previous
session. Its official close is read instead straight from the archived index-close file (G13b's own `IndexFileCloses`
over the raw-file library), which the morning routine archives first with A9's librarian (orchestrator, 22 Oct)."""

from __future__ import annotations

from datetime import date

from ..price_ranges.closes import IndexFileCloses
from .ranges import Outcomes


class ArchivedCloses(Outcomes):
    def __init__(self, tables: Outcomes, files: IndexFileCloses):
        self.tables, self.files = tables, files

    def close(self, underlying: str, day: date) -> float | None:
        known = self.tables.close(underlying, day)
        if known is not None:
            return known
        found, _ = self.files.rows_for(underlying, [day])
        return found[0][1] if found else None
