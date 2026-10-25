"""The flow-history table (story A23, scope 2-3): every archived session not yet in the table gets its write time
(A8's `LastWriteSweep`, logged in the repository), its point-in-time dates and its values, in one new O9 part per
run. A session whose write time could not be asked (NSE unreachable) waits for the next run; one NSE serves without a
`Last-Modified` is entered as `rewritten` (unknown). A damaged archived file is named, never entered."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from ..fo_bhavcopy import BadFile
from ..research_data.write_sweep import NO_LAST_MODIFIED, LastWriteSweep
from ..storage.part_table import PartTable
from ..storage.raw_store import RawFileStore
from .availability import availability
from .values import FlowValues

COLUMNS = ("session", "dataset", "last_modified", "available_from", "rewritten", "series", "measure", "value")
TABLE = "flows/history/{name}"  # one table per dataset
NEVER_ASKED = datetime(2000, 1, 1, tzinfo=UTC)  # below any write time: the sweep logs every day it is given
YES, NO = "yes", "no"


@dataclass
class TableResult:
    entered: list[date] = field(default_factory=list)
    rewritten: list[date] = field(default_factory=list)
    waiting: dict[date, str] = field(default_factory=dict)  # day -> why it is not entered yet
    stopped: str = ""

    @property
    def problems(self) -> list[str]:
        lines = [f"{day} waits: {why}" for day, why in sorted(self.waiting.items())]
        return lines + ([self.stopped] if self.stopped else [])


class FlowTableJob:
    def __init__(self, values: FlowValues, raw: RawFileStore, sweep: LastWriteSweep,
                 logged: Callable[[], dict[date, datetime]], next_session: Callable[[date], date], table: PartTable,
                 today: Callable[[], date]):  # fmt: skip
        """`raw`: the archive's raw area; `logged`: the write-time log (day -> latest write)."""
        self.values, self.raw, self.sweep, self.logged = values, raw, sweep, logged
        self.next_session, self.table, self.today = next_session, table, today

    def run(self, archived: Iterable[date], entered: set[date]) -> TableResult:
        result, pending = TableResult(), sorted(set(archived) - entered)
        swept = self.sweep.run({day: NEVER_ASKED for day in pending if day not in self.logged()})
        result.stopped, written = swept.stopped, self.logged()
        rows = []
        for day in pending:
            if day not in written and swept.unanswered.get(day) != NO_LAST_MODIFIED:
                result.waiting[day] = swept.unanswered.get(day, "write time not asked (the pass stopped)")
                continue
            try:
                rows += self._rows(day, written.get(day), result)
            except (BadFile, LookupError) as problem:
                result.waiting[day] = str(problem)
        if rows:
            self.table.write(self.today(), rows)
        return result

    def _rows(self, day: date, last_modified: datetime | None, result: TableResult) -> list[dict]:
        path = self.values.source.path_for(day)
        data = self.raw.get(path)
        if data is None:
            raise LookupError(f"{path} is in the manifest but not in Drive")
        triples = self.values.values(data, day)  # first: a damaged file raises before anything is counted
        dates = availability(day, last_modified, self.next_session)
        result.entered.append(day)
        if dates.rewritten:
            result.rewritten.append(day)
        common = {
            "session": day.isoformat(),
            "dataset": self.values.source.dataset,
            "last_modified": last_modified.isoformat() if last_modified else "",
            "available_from": dates.available_from.isoformat(),
            "rewritten": YES if dates.rewritten else NO,
        }
        return [common | {"series": s, "measure": m, "value": v} for s, m, v in triples]
