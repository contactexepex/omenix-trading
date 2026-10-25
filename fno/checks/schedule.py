"""Which capture a decision executes at, its window and its committed capture record (story C3, judge 81 ruling 2).
E3 will give its own execution capture and record through `ExecutionSchedule` without changing C3; until then the
desk's capture is the common pack's A4 snapshot, in the recorder's window, recorded by the pack's provenance (the pack
is written once and committed, with its own SHA-256)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..desk.common_pack import SNAPSHOT_INPUT, CommonPack
from ..models import IST
from ..quotes.recorder import WINDOW_END, WINDOW_START
from .data_checks import CaptureRecord, ScheduledCapture


class ExecutionSchedule(ABC):
    @abstractmethod
    def capture(self, pack: CommonPack) -> ScheduledCapture | None:
        """The capture the day's decisions execute at, with its window and record; None when there is none."""


class PackSnapshotSchedule(ExecutionSchedule):
    """The A4 snapshot the common pack holds, inside the recorder's window (14:55-15:10 IST)."""

    def capture(self, pack: CommonPack) -> ScheduledCapture | None:
        provenance = pack.body["provenance"].get(SNAPSHOT_INPUT, {})
        snapshot_id = provenance.get("snapshot_id")
        if snapshot_id is None:
            return None
        start, end = (datetime.combine(pack.day, moment, IST) for moment in (WINDOW_START, WINDOW_END))
        source = f"common pack {pack.day} (sha256 {pack.sha256})"
        record = CaptureRecord(snapshot_id, provenance.get("csv_sha256", ""), provenance.get("meta_sha256", ""), source)
        return ScheduledCapture(snapshot_id, start, end, record)
