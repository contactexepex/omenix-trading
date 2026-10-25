"""One run over the cues (story A17): for each, download, archive and extend its table; then rewrite the checks.

A cue that fails writes nothing and is named; the others still run. The default range starts 31 days before a
table's last date (so late values and revisions are seen) or, for an empty table, at the source's first date.
"""

from __future__ import annotations

from datetime import date, timedelta

import requests

from ..research_data.calendar import CalendarError
from ..storage.owner_token import DriveSignInRefused
from ..storage.row_log import TableFileBroken
from .check_files import CueChecks
from .collector import CueCollector
from .source import GlobalCueSource
from .table import CueTable

LOOK_BACK = timedelta(days=31)
RUN_STOPPERS = (TableFileBroken, OSError, RuntimeError, DriveSignInRefused, requests.RequestException, CalendarError)


class GlobalCueJob:
    def __init__(self, collector: CueCollector, tables: dict[str, CueTable], checks: CueChecks):
        self.collector, self.tables, self.checks = collector, tables, checks

    def run(self, sources: list[GlobalCueSource], start: date | None, end: date) -> tuple[list[str], bool]:
        lines, ok = [], True
        for source in sources:
            try:
                line, cue_ok = self._run_cue(source, start, end)
            except RUN_STOPPERS as exc:  # what earlier cues wrote is still reported below
                lines.append(f"{source.cue}: FAILED, run stopped ({type(exc).__name__}): {exc}")
                ok = False
                break
            lines.append(line)
            ok = ok and cue_ok
        checked, checks_ok = self._checks()
        return [*lines, *checked], ok and checks_ok

    def _checks(self) -> tuple[list[str], bool]:
        """The checks; a failure there never hides the cue lines above it."""
        try:
            return self.checks.write(), True
        except (*RUN_STOPPERS, ValueError) as exc:  # ValueError: a damaged cell (named, never shown: `positive`)
            return [f"checks FAILED ({type(exc).__name__}): {exc}"], False

    def _run_cue(self, source: GlobalCueSource, start: date | None, end: date) -> tuple[str, bool]:
        table = self.tables[source.cue]
        collection = self.collector.collect(source, start or _default_start(source, table), end)
        if collection.failure:
            return f"{source.cue}: FAILED, {collection.failure}", False
        return self._merge(source, table, collection, end)

    def adopt(self, source: GlobalCueSource, path: str, start: date, end: date) -> tuple[list[str], bool]:
        """Takes a copy already in Drive into the cue's log and table, first seen at its own fetch time."""
        collection = self.collector.copies.adopt(source, path, start, end)
        if collection.failure:
            return [f"{source.cue}: FAILED, {collection.failure}"], False
        line, _ = self._merge(source, self.tables[source.cue], collection, end)
        checked, checks_ok = self._checks()
        return [line, *checked], checks_ok

    def _merge(self, source: GlobalCueSource, table: CueTable, collection, end: date) -> tuple[str, bool]:
        done = collection.skipped or _merged(table, collection)
        rows = table.rows()
        last = date.fromisoformat(rows[-1]["value_date"]) if rows else None
        line = f"{source.cue}: {done}, last {last}"
        if last is None or (end - last).days > source.max_age_days:
            return f"{line}; STALE: older than {source.max_age_days} days on {end}", False
        return line, True


def _merged(table: CueTable, collection) -> str:
    merged = table.merge(collection.values, collection.fetched_at)
    return f"{merged.added} dates added, {merged.revisions} revisions logged"


def _default_start(source: GlobalCueSource, table: CueTable) -> date:
    rows = table.rows()
    return date.fromisoformat(rows[-1]["value_date"]) - LOOK_BACK if rows else source.first_value_date
