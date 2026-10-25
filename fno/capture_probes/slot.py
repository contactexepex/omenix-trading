"""One slot of the probe (story MS-P0b sections 3-5): reserve both sources' budgets and push the reservation, then
Groww's part, then NSE's, each through its own `PacedCaller`; save each part's raw answers once in Drive, count them,
and push the counts. A reservation that cannot be pushed starts no request (judge 626)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

from .archive import CONFLICT, SlotArchive
from .caller import PacedCaller, SourceStopped
from .constants import (
    CAP_LINE,
    CHAINS,
    DAILY_CAP,
    FUTURES,
    OPTION_TYPES,
    RESERVATION_NOT_PUSHED,
    SLOT_BUDGET,
    SLOT_LINE,
    STRIKES_EACH_SIDE,
    Quality,
    Source,
)
from .counts import CountsFolder, DayCounts, SourceSlot
from .groww_reader import GrowwReader
from .nse_reader import NseReader
from .pace import StudyPace
from .publish import Publisher
from .rows import flags_of
from .slot_capture import SlotCapture
from .stops import StopRecorder

PLANNED_ROWS = len(FUTURES) + len(CHAINS) * (2 * STRIKES_EACH_SIDE + 1) * len(OPTION_TYPES)
RATE_REASON = "HTTP 429"
CONFLICT_LINE = "p0b slot {slot} {source}: Drive already holds other bytes for this slot; not saved"


@dataclass
class SlotTools:
    """What every slot uses: the readers, one pace per source, the clocks and the record writers."""

    groww: GrowwReader
    nse: NseReader
    paces: dict[Source, StudyPace]
    wall_clock: Callable[[], datetime]
    timer: Callable[[], float]
    sleep: Callable[[float], None]
    archive: SlotArchive
    folder: CountsFolder
    publisher: Publisher
    stops: StopRecorder
    disabled: set[Source] = field(default_factory=set)


class SlotRunner:
    def __init__(self, tools: SlotTools):
        self.tools = tools

    def run(self, session: date, name: str, counts: DayCounts, deadline: datetime) -> list[str]:
        live = [s for s in Source if s not in counts.stops and s not in self.tools.disabled]
        if not live:
            return []
        counts.slots[name] = {source: SourceSlot(reserved=self._reservation(source, counts)) for source in live}
        self.tools.folder.write(counts)
        if reason := self.tools.publisher.publish(f"{session} slot {name} reserved"):
            del counts.slots[name]
            self.tools.folder.write(counts)
            return [RESERVATION_NOT_PUSHED.format(slot=name, reason=reason)]
        lines = []
        for source in live:
            lines += self._run_source(session, name, source, counts, deadline)
        self.tools.folder.write(counts)
        if reason := self.tools.publisher.publish(f"{session} slot {name} counts"):
            lines.append(reason)
        return lines

    def _wanted(self, source: Source) -> int:
        lookups = len(self.tools.groww.unlooked()) if source is Source.GROWW else 0
        return SLOT_BUDGET[source] + lookups

    def _reservation(self, source: Source, counts: DayCounts) -> int:
        return max(0, min(self._wanted(source), DAILY_CAP[source] - counts.spent(source)))

    def _run_source(self, session: date, name: str, source: Source, counts: DayCounts, deadline) -> list[str]:
        entry = counts.slots[name][source]
        cut = entry.reserved < self._wanted(source)
        earlier = sum(slot[source].refusals.get(RATE_REASON, 0) for key, slot in counts.slots.items()
                      if key != name and source in slot)  # fmt: skip
        tools = self.tools
        caller = PacedCaller(tools.paces[source], entry.reserved, deadline, tools.wall_clock, tools.timer,
                             tools.sleep, first_429_stops=source is Source.GROWW, earlier_429s=earlier,
                             cap_reason=CAP_LINE.format(cap=DAILY_CAP[source]) if cut else "")  # fmt: skip
        capture, lines = SlotCapture(), []
        try:
            self._read(source, caller, capture, session)
        except SourceStopped as stopped:
            lines += self._stop(session, name, source, counts, stopped.reason)
        drive = tools.archive.save(source, str(session), name, capture.all_lines())
        if drive == CONFLICT:
            lines.append(CONFLICT_LINE.format(slot=name, source=source))
        self._count(entry, caller, capture, drive)
        ok = entry.quality.get(Quality.OK, 0)
        lines.insert(0, SLOT_LINE.format(slot=name, source=source, used=entry.used, ok=ok, rows=entry.rows,
                                         stop=entry.stop or "no stop"))  # fmt: skip
        return lines

    def _stop(self, session: date, name: str, source: Source, counts: DayCounts, reason: str) -> list[str]:
        """Records the stop and pushes it at once, before anything else runs: a run that dies later must not leave a
        rerun free to ask the stopped source again (self-review 2)."""
        lines = self.tools.stops.stopped(session, source, name, reason)
        counts.stops[source], counts.slots[name][source].stop = lines[0], reason
        self.tools.folder.write(counts)
        if failed := self.tools.publisher.publish(f"{session} {source} stopped"):
            lines.append(failed)
        return lines

    def _read(self, source: Source, caller: PacedCaller, capture: SlotCapture, session: date) -> None:
        if source is Source.NSE:
            self.tools.nse.read_slot(caller, capture, session)
            return
        if self.tools.groww.unlooked():
            self.tools.groww.read_expiries(caller, session)
        self.tools.groww.read_slot(caller, capture)

    @staticmethod
    def _count(entry: SourceSlot, caller: PacedCaller, capture: SlotCapture, drive: str) -> None:
        quality = Counter(flag for row in capture.rows for flag in flags_of(row))
        unread = PLANNED_ROWS - len(capture.rows)
        if unread > 0:
            quality[Quality.MISSING] += unread
        entry.used, entry.refusals, entry.rows = caller.sent, dict(caller.refusals), PLANNED_ROWS
        entry.quality, entry.latency_ms, entry.drive = dict(quality), caller.latency_ms(), drive
