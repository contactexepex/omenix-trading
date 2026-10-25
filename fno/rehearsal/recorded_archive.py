"""NSE's archive in a rehearsal (story REH1h, DRY2's gap G2b): a file the day's own routine archived is served from
the record, near its row's commit. Each URL's candidates are the record's A9 manifest rows for it (`ManifestRows`)
that reached main on the replayed day (IST) no later than `serving.NEAREST` after now, each at its dataset's own path
for the row's day, kept only when that path maps back to the URL.

- A candidate that reached main after now is the day's own read in this run: the earliest is served, once the replay
  clock reaches its commit (a real wait: the A9 rows hold no fetch time, and the commit is the first moment the record
  proves the file was held, so it is never served earlier).
- Else the latest that reached main at or before now that day: the copy the record held then. For a fetch-first read
  (a session-filed taker) that is what it would have been served (not always NSE's newest: a 22 Oct by-session read
  at 19:40 gets the 21 Oct session's copy that reached main on 22 Oct); a store-first read of a dated URL never gets
  here, since REH1g's visibility already shows the file.
- A list filed by the run's day (the reference lists, the run-dated flows) has one URL every day, so only the row
  for the replayed day itself is a candidate: another day's copy that reached main late is never filed as today's.
- Two candidates at the chosen commit time with different SHA-256 (two datasets sharing one URL) are refused as
  ambiguous, never guessed. A repeat request for a URL gets the copy it got first (a scheduled read, unlike the paced
  `ServedOnce`).

The bytes come from the real Drive record, read-only, and must hash to the row's SHA-256. Anything else (no
candidate, every HEAD request) is the same "not recorded" as REH1b's `NotRecordedSession`: a request never sent."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date, datetime

from ..models import IST
from ..storage.content_checks import COVERED_SESSION
from ..storage.snapshot_source import SnapshotSource
from ..storage.source_lists import RAW_SOURCES, dataset_name
from .manifest_rows import A9Row, ManifestRows
from .nse_wiring import NotRecorded, NotRecordedSession
from .recorded_cues import RecordedAnswer
from .serving import NEAREST

SOURCES = {dataset_name(source): source for source in RAW_SOURCES}
AMBIGUOUS = "rehearsal: {url}: two recorded copies reached main at {at} and differ ({paths}); refused, never guessed"
DAMAGED = "rehearsal: the recorded copy {path} is missing from Drive or differs from its manifest row"
UNREAD = "rehearsal: the recorded copy {path} could not be read from Drive: {error}"


class RecordedArchiveSession(NotRecordedSession):
    def __init__(self, rows: ManifestRows, day: date, read: Callable[[str], bytes | None],
                 now: Callable[[], datetime], sleep: Callable[[float], None]):  # fmt: skip
        """`read`: a raw-area path of the real Drive record, read-only; `day`: the replayed day."""
        super().__init__()
        self.rows, self.day, self.read, self.now, self.sleep = rows, day, read, now, sleep
        self.served: dict[str, A9Row] = {}

    def get(self, url, *args, **kwargs) -> RecordedAnswer:
        row = self.served.get(url) or self._pick(url)
        if row is None:
            return super().get(url)
        if (wait := (row.committed - self.now()).total_seconds()) > 0:
            self.sleep(wait)
        path = path_of(row)
        try:
            data = self.read(path)
        except Exception as exc:  # no Drive settings, Drive down: the step's refused line, never a crash
            raise NotRecorded(UNREAD.format(path=path, error=exc)) from exc
        if data is None or hashlib.sha256(data).hexdigest() != row.sha256:
            raise NotRecorded(DAMAGED.format(path=path))
        self.served[url] = row
        return RecordedAnswer(data)

    def _pick(self, url: str) -> A9Row | None:
        now = self.now()
        candidates = [row for row in self.rows.archived(url) if self._is_candidate(row, now)]
        if not candidates:
            return None
        ahead = [row for row in candidates if row.committed > now]
        at = min(row.committed for row in ahead) if ahead else max(row.committed for row in candidates)
        chosen = [row for row in candidates if row.committed == at]
        if len({row.sha256 for row in chosen}) > 1:
            paths = ", ".join(path_of(row) for row in chosen)
            raise NotRecorded(AMBIGUOUS.format(url=url, at=at.astimezone(IST).isoformat(), paths=paths))
        return chosen[0]

    def _is_candidate(self, row: A9Row, now: datetime) -> bool:
        if row.committed.astimezone(IST).date() != self.day or row.committed > now + NEAREST:
            return False
        source = SOURCES.get(row.dataset)
        if source is None or (is_run_dated(source) and row.day != self.day):
            return False  # a list filed by the run's day: only the replayed day's own copy (never another day's)
        try:  # a dataset whose path the URL alone cannot give (a symbol's own list) is never a candidate
            return source.url_for(path_of(row)) == row.url
        except ValueError:
            return False


def is_run_dated(source) -> bool:
    """A fixed-URL list filed under the day it was taken (`SnapshotTaker`), not under the session it covers."""
    return issubclass(source, SnapshotSource) and source not in COVERED_SESSION


def path_of(row: A9Row) -> str:
    """The row's file inside the raw area: its dataset's own path for the row's day."""
    return SOURCES[row.dataset].path_for(row.day)
