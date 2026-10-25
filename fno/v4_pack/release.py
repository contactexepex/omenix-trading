"""A day's release record (story G10 part 2, section 2): which pack every family reads, written once in Drive right
after the pack, `v4/days/<YYYY>/<date>.json`. Part 1's day format (G8 reads it with `parse_day`) plus `pack_path`;
`system_late` days name no pack. Readers get the record and the pack only through the verified Drive cache (O9)."""

from __future__ import annotations

import json
import posixpath
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..constants import V4_DAY_SYSTEM_LATE
from ..forecast_scoring.v4.days import DayFileError, parse_day
from ..storage.data_store import DataStore
from ..storage.drive_cache import DriveCache
from .codec import pack_bytes, pack_sha256, read_pack
from .model import Pack
from .paths import pack_path, release_path

NO_RECORD = "{day}: no release record in the receipts (no pack released, no fire)"
UNVERIFIED = "{day}: the release record or its pack could not be verified: {problems}"
LATE = "{day}: system_late, no pack was released"


class NotReleased(RuntimeError):
    """No usable pack for the day: no record, a system_late record, or bytes that fail verification."""


@dataclass(frozen=True)
class ReleaseRecord:
    day: date
    label: str
    pack_path: str  # "" on a system_late day
    pack_sha256: str  # "" on a system_late day
    observed_by: datetime | None  # the pack's latest observed_at

    def to_bytes(self) -> bytes:
        body = {"day": self.day.isoformat(), "label": self.label, "pack_path": self.pack_path,
                "pack_sha256": self.pack_sha256,
                "observed_by": self.observed_by.isoformat() if self.observed_by else ""}  # fmt: skip
        return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def released(pack: Pack) -> tuple[bytes, ReleaseRecord]:
    """The pack's stored bytes and the record that releases them."""
    data = pack_bytes(pack)
    return data, ReleaseRecord(pack.day, pack.label, pack_path(pack.day), pack_sha256(data), pack.observed_by())


def late(day: date) -> ReleaseRecord:
    return ReleaseRecord(day, V4_DAY_SYSTEM_LATE, "", "", None)


def publish(store: DataStore, day: date, pack: Pack | None,
            in_time: Callable[[], bool] = lambda: True) -> ReleaseRecord:  # fmt: skip
    """Writes the pack, then its release record (a day with no complete pack: a system_late record only). `in_time()`
    is asked after the pack's upload, right before the small record is written (G10 completion, judge 584 m2): a slow
    upload past the release-by time makes the record `system_late` and leaves the pack unreleased (write-once, named by
    no record). Committing the receipts is the caller's step; the record's receipt push is what starts the AI fire."""
    record = late(day)
    if pack is not None:
        data, ready = released(pack)
        store.put(ready.pack_path, data)
        record = ready if in_time() else record
    store.put(release_path(day), record.to_bytes())
    return record


def parse_release(stem: str, data: bytes) -> ReleaseRecord:
    body = json.loads(data.decode("utf-8"))
    label = parse_day(stem, body)
    path = body.get("pack_path") or ""
    if (label.label == V4_DAY_SYSTEM_LATE) != (path == "") or (path and path != pack_path(label.day)):
        raise DayFileError(f"{stem}: pack_path {path!r} does not fit the label {label.label}")
    return ReleaseRecord(label.day, label.label, path, label.pack_sha256, label.observed_by)


class ReleasedPacks:
    """The released record and pack of a day, verified against their receipts before any byte is used."""

    def __init__(self, cache: DriveCache, area: str):
        self.cache, self.area = cache, area

    def release(self, day: date) -> ReleaseRecord:
        return parse_release(day.isoformat(), self._verified(day, release_path(day)))

    def pack_bytes(self, release: ReleaseRecord) -> bytes:
        if release.label == V4_DAY_SYSTEM_LATE:
            raise NotReleased(LATE.format(day=release.day))
        data = self._verified(release.day, release.pack_path)
        read_pack(data, release.pack_sha256)
        return data

    def pack(self, release: ReleaseRecord) -> Pack:
        return read_pack(self.pack_bytes(release), release.pack_sha256)

    def _verified(self, day: date, path: str) -> bytes:
        drive_path = f"{self.area}/{path}"
        if self.cache.receipts.read(drive_path) is None:
            raise NotReleased(NO_RECORD.format(day=day))
        report = self.cache.sync(posixpath.dirname(drive_path))
        mine = [p for p in report.problems if p.startswith(drive_path + ":")]
        if mine:
            raise NotReleased(UNVERIFIED.format(day=day, problems="; ".join(mine)))
        return Path(self.cache.local(drive_path)).read_bytes()
