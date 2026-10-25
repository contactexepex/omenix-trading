"""Which committed capture a decision was made on (story C4): the day's written common pack (E2), checked against its
own `.sha256` file, then C3's execution schedule names the capture and its record. No pack, or a pack whose hash
differs, names nothing, so the evidence check fails."""

from __future__ import annotations

import json
from datetime import date

from ..desk.common_pack import CommonPack
from ..desk.pack_items import sha256_hex
from ..desk.pack_store import PackStore
from .data_checks import CaptureRecord
from .schedule import ExecutionSchedule


class PackCaptures:
    def __init__(self, packs: PackStore, schedule: ExecutionSchedule):
        self.packs, self.schedule = packs, schedule

    def record(self, day: date) -> CaptureRecord | None:
        path = self.packs.common_path(day)
        hash_file = path.with_suffix(".sha256")
        if not path.is_file() or not hash_file.is_file():
            return None
        data = path.read_bytes()
        if hash_file.read_text(encoding="utf-8").split()[:1] != [sha256_hex(data)]:
            return None
        pack = CommonPack(day, json.loads(data))
        capture = self.schedule.capture(pack)
        return capture.record if capture else None
