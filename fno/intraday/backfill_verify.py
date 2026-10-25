"""`backfill-verify` (story A16b): every candle-close row recomputed from the Drive copies it names, read-only (no
Groww, nothing archived). A copy missing from Drive or the manifest, bytes that differ from the manifest, or a row that
differs from its recomputation is named. Uses the run's own rules (deriver, previous close), never a copy of them."""

from __future__ import annotations

from datetime import date

from ..research_data.calendar import SessionCalendar
from .backfill import STORE_FAILURES, first_recorded_session
from .candle_archive import CandleArchive, CopyDamaged
from .candle_rv_table import CandleRvTable
from .nse_days import NseDays, NseReadFailed
from .previous_close import PreviousClose
from .session_deriver import SessionDeriver, SessionInputs
from .session_rv import previous_recorded_session


class CandleRowVerifier:
    def __init__(self, archive: CandleArchive, nse: NseDays, table: CandleRvTable, deriver: SessionDeriver,
                 calendar: SessionCalendar, series_start: date):  # fmt: skip
        self.archive, self.nse, self.table, self.deriver, self.calendar = archive, nse, table, deriver, calendar
        self.previous, self.first = PreviousClose(archive, deriver), first_recorded_session(calendar, series_start)

    def problems(self) -> list[str]:
        rows = {date.fromisoformat(r["session"]): r for r in self.table.rows()}
        found = []
        for day, row in sorted(rows.items()):
            try:
                found += self._check(day, row, rows)
            except (*STORE_FAILURES, NseReadFailed) as failed:
                named = isinstance(failed, (NseReadFailed, CopyDamaged))  # our own path and reason, never a secret
                found.append(f"{day}: not verified: {failed if named else type(failed).__name__}")
        return found

    def _check(self, day: date, row: dict, rows: dict) -> list[str]:
        copies = []
        for path in (row["copy_15m"], row["copy_1m"]):
            manifest_row = self.archive.row_for(path) if path else None
            if path and manifest_row is None:
                return [f"{day}: {path} has no manifest row"]
            copies.append(self.archive.load(manifest_row) if manifest_row else None)
        previous_close = None
        if day != self.first:
            previous = rows.get(previous_recorded_session(self.calendar, day))
            if previous is None:
                return [f"{day}: its previous session has no row"]
            previous_close = self.previous.of(previous)
        again = self.deriver.derive(SessionInputs(day, copies[0], copies[1], self.nse.read(day), previous_close))
        differing = [k for k, v in again.items() if str(v) != row.get(k, "")]
        return [f"{day}: differs from its copies in {', '.join(differing)}"] if differing else []
