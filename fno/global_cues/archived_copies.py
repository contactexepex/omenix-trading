"""Copies already in the raw archive, read back instead of downloaded (story A17).

- `adopt`: a copy saved before it was logged (the four US-index files fetched before their terms were read, kept by
  the owner): logged with the fetch time in its own path and the request its name matches, then read. The store's own
  creation time of the copy must fall within `ADOPT_WINDOW` after that path time (story A17b), so a renamed or
  re-uploaded file never gets an earlier `first_seen_at`; a store that cannot say refuses.
- `reuse_today`: the once-a-day rule's other half. A second run on the same IST date downloads nothing and reads the
  day's logged copy again, so a run whose table write failed can finish later that day with the copy's true
  `first_seen_at` (never a later one).
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from ..models import IST, now_ist
from ..storage.creation_times import CreationTimes
from ..storage.raw_store import RawFileStore
from .collection import UNREADABLE, Collection, SourcedValue, final_values
from .snapshot_log import SnapshotLog, SnapshotRow
from .source import GlobalCueSource

COPY_TIME = "%Y/%m/%d/%H%M%S"  # a copy's fetch time, from its path `<YYYY>/<MM>/<DD>/<HHMMSS>_<name>` (IST)
COPY_PATH = "<dataset>/<YYYY>/<MM>/<DD>/<HHMMSS>_<name>"
ADOPT_WINDOW = timedelta(minutes=10)  # an upload ends seconds after its fetch (the four adopted: 4 to 9 s)


class ArchivedCopies:
    def __init__(self, store: RawFileStore, log: SnapshotLog, created: CreationTimes | None):
        """`created`: the store's creation times; None when the store cannot give them (adopt then refuses)."""
        self.store, self.log, self.created = store, log, created

    def adopt(self, source: GlobalCueSource, path: str, start: date, end: date) -> Collection:
        result = Collection(source.cue, now_ist())
        try:
            result.fetched_at = datetime.strptime("/".join(path.split("/")[-4:])[:17], COPY_TIME).replace(tzinfo=IST)
            name = path.rsplit("/", 1)[-1].split("_", 1)[1]
        except (ValueError, IndexError):
            result.failure = f"cannot adopt {path}: not a copy path {COPY_PATH}"
            return result
        request = next((r for r in source.requests(start, end) if r.name == name), None)
        if not path.startswith(f"{source.dataset}/") or request is None:
            result.failure = (
                f"cannot adopt {path}: not {source.cue}'s dataset, or no request named {name} for {start}-{end}"
            )
            return result
        result.failure = self._creation_mismatch(path, result.fetched_at)
        if result.failure:
            return result
        data = self._read(source, path, start, end, result)
        if data is not None and path not in self.log.paths(source.cue):  # every copy logged once
            sha256 = hashlib.sha256(data).hexdigest()
            self.log.append(
                source.cue, SnapshotRow(result.fetched_at, path, request.url, request.form, sha256, len(data))
            )
        return result

    def _creation_mismatch(self, path: str, path_time: datetime) -> str:
        created = self.created.created_at(path) if self.created else None
        if created is None:
            return f"cannot adopt {path}: the store cannot give its creation time"
        if not path_time <= created <= path_time + ADOPT_WINDOW:
            return (
                f"cannot adopt {path}: created {created.astimezone(IST).isoformat()}, "
                f"not within {ADOPT_WINDOW} after its path time {path_time.isoformat()}"
            )
        return ""

    def reuse_today(self, source: GlobalCueSource, day: date, start: date, end: date) -> Collection:
        fetched_at, paths = self.log.latest_fetch_on(source.cue, day)
        result = Collection(source.cue, fetched_at)
        for path in paths:
            if self._read(source, path, start, end, result) is None:
                return result
        result.skipped = f"no download: today's copy of {fetched_at:%H:%M:%S} IST read again (at most once a day)"
        return result

    def _read(self, source: GlobalCueSource, path: str, start: date, end: date, result: Collection) -> bytes | None:
        """Adds the copy's final values in range to `result`; names the failure and returns None when unreadable."""
        data = self.store.get(path)
        if data is None:
            result.failure = f"{path} is not in the archive"
            return None
        try:
            values = final_values(source, source.parse(data), result.fetched_at)
        except UNREADABLE as exc:
            result.failure = f"{path} is not the publisher's file: {exc}"
            return None
        sha256 = hashlib.sha256(data).hexdigest()
        result.values += [SourcedValue(v, sha256) for v in values if start <= v.value_date <= end]
        return data
