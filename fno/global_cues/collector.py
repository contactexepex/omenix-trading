"""Downloads one cue's files, checks them, archives them raw and logs them (story A17).

All of a cue's files are downloaded and read before anything is saved: one failed download or one file that is not
the publisher's writes nothing for that cue, and the failure is named. A saved copy is filed under the time it was
fetched (`<dataset>/<YYYY>/<MM>/<DD>/<HHMMSS>_<name>`, IST), because these publishers replace their files in place: a
copy is never overwritten, and a later copy that changes a past value is kept beside the earlier one (A11's rule; the
table records the change, `table.py`). Every saved copy gets a row in the cue's snapshot log in the same operation.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date, datetime

import requests

from ..models import IST
from ..storage.creation_times import CreationTimes
from ..storage.raw_store import RawFileConflict, RawFileStore, StoredCopyDamaged
from .archived_copies import ArchivedCopies
from .attempt_log import (
    DOWNLOAD_FAILED,
    MAX_ATTEMPTS,
    NO_VALUES,
    NOT_PUBLISHERS_FILE,
    SAVE_FAILED,
    SAVED,
    STARTED,
    STOPPED,
    AttemptLog,
)
from .collection import UNREADABLE, Collection, SourcedValue, final_values
from .snapshot_log import SnapshotLog, SnapshotRow
from .source import GlobalCueSource

SAVE_FAILURES = (RawFileConflict, StoredCopyDamaged, requests.RequestException)  # Drive refused or failed the copy
ATTEMPTS_FOLDER = "attempts"  # beside the snapshot logs: `<log folder>/attempts/<cue>.csv`


class CueCollector:
    def __init__(
        self,
        session: requests.Session,
        store: RawFileStore,
        log: SnapshotLog,
        clock: Callable[[], datetime],
        created: CreationTimes | None = None,
    ):
        """`created`: the raw store's creation times, for adopt; None refuses every adopt."""
        self.session, self.store, self.log, self.clock = session, store, log, clock
        self.copies = ArchivedCopies(store, log, created)
        self.attempts = AttemptLog(log.folder / ATTEMPTS_FOLDER)

    def collect(self, source: GlobalCueSource, start: date, end: date) -> Collection:
        started = self.clock()
        if not source.once_a_day:
            return self._download(source, start, end, Collection(source.cue, started))[0]
        day = started.astimezone(IST).date()
        if self.log.fetched_on(source.cue, day):  # a saved copy ends the day's downloads
            return self.copies.reuse_today(source, day, start, end)
        if self.attempts.count_on(source.cue, day) >= MAX_ATTEMPTS:
            capped = Collection(source.cue, started)
            capped.failure = f"no download: {MAX_ATTEMPTS} attempts today already, none saved (at most {MAX_ATTEMPTS})"
            return capped
        return self._logged_attempt(source, start, end, started)

    def _logged_attempt(self, source: GlobalCueSource, start: date, end: date, started: datetime) -> Collection:
        """Downloads once, logged as `started` first (a killed run still counts against the day's cap) and then with
        its outcome; an unexpected failure is logged `stopped` and raised. A broken log never lets a download by."""
        self.attempts.append(source.cue, started, STARTED)  # raises on a broken log: no download then
        outcome = STOPPED
        try:
            result, outcome = self._download(source, start, end, Collection(source.cue, started))
            return result
        finally:
            self.attempts.append(source.cue, started, outcome)

    def _download(self, source: GlobalCueSource, start: date, end: date, result: Collection) -> tuple[Collection, str]:
        """The collection and the attempt's outcome (`attempt_log`'s names)."""
        downloaded = []
        for request in source.requests(start, end):
            try:
                data = source.download(self.session, request)
                values = source.parse(data)
            except requests.RequestException as exc:
                result.failure = f"download failed, nothing saved: {request.url}: {exc}"
                return result, DOWNLOAD_FAILED
            except UNREADABLE as exc:
                result.failure = f"not the publisher's file, nothing saved: {request.name}: {exc}"
                return result, NOT_PUBLISHERS_FILE
            downloaded.append((request, data, values))
        result.fetched_at = self.clock()  # after the last download: a slow fetch is never labelled earlier than it was
        if not any(values for _, _, values in downloaded):
            result.failure = "no values in any file, nothing saved"
            return result, NO_VALUES
        values = []
        for done, (request, data, file_values) in enumerate(downloaded):
            try:
                sha256 = self._archive(source, request, data, result.fetched_at)
            except SAVE_FAILURES as exc:  # copies saved before it stay saved and logged; the table is not touched
                result.failure = f"saving failed after {done} of {len(downloaded)} copies: {request.name}: {exc}"
                return result, SAVE_FAILED
            final = final_values(source, file_values, result.fetched_at)
            values += [SourcedValue(v, sha256) for v in final if start <= v.value_date <= end]
        result.values = values
        return result, SAVED

    def _archive(self, source: GlobalCueSource, request, data: bytes, fetched_at: datetime) -> str:
        path = f"{source.dataset}/{fetched_at:%Y/%m/%d}/{fetched_at:%H%M%S}_{request.name}"
        sha256 = hashlib.sha256(data).hexdigest()
        self.store.put(path, data)
        self.log.append(source.cue, SnapshotRow(fetched_at, path, request.url, request.form, sha256, len(data)))
        return sha256
