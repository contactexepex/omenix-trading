"""A17e's Yahoo reads in a rehearsal (story REH1c), behind the cue jobs' HTTP session: each URL is answered with the
copy the day archived for it nearest to now, each copy once and in order (`serving.ServedOnce`, per URL), once the
replay clock reaches its fetch time. The copy is found in the record checkout's snapshot logs
(`research/data/manifests/global-cues/`) and read from the real Drive's `raw` area, checked against the row's SHA-256.
A URL the day never fetched near then is "not recorded": a request that is never sent, which the readers already count
as that cue's failure."""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .nse_wiring import NotRecorded
from .serving import ServedOnce

NOT_RECORDED = "rehearsal:NOT_RECORDED {url} at {at}: the day archived no copy near then"
DAMAGED = "rehearsal: the recorded copy {path} is missing from Drive or differs from its snapshot-log row"


class RecordedAnswer:
    """What the cue readers and NSE's archive sources ask of an answer: a 200 with the recorded bytes, never a
    redirect, and no publisher headers (so no Last-Modified: a recorded file's "last written" time is unknown)."""

    status_code, is_redirect = 200, False

    def __init__(self, content: bytes):
        self.content = content
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        return None


class RecordedCueSession:
    def __init__(self, logs: Path, read: Callable[[str], bytes | None], now: Callable[[], datetime],
                 sleep: Callable[[float], None]):  # fmt: skip
        self.logs, self.read, self.now, self.sleep = Path(logs), read, now, sleep
        self.headers: dict[str, str] = {}
        self.served: dict[str, ServedOnce] = {}

    def get(self, url, *args, **kwargs) -> RecordedAnswer:
        now = self.now()
        row = self._row(url, now)
        if row is None:
            raise NotRecorded(NOT_RECORDED.format(url=url, at=now.isoformat()))
        if (wait := (datetime.fromisoformat(row["fetched_at"]) - self.now()).total_seconds()) > 0:
            self.sleep(wait)
        data = self.read(row["path"])
        if data is None or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise NotRecorded(DAMAGED.format(path=row["path"]))
        return RecordedAnswer(data)

    def _row(self, url: str, now: datetime) -> dict | None:
        rows = []
        for log in sorted(self.logs.glob("*.csv")) if self.logs.is_dir() else ():
            rows += csv.DictReader(io.StringIO(log.read_text(encoding="utf-8")))
        copies = {r["path"]: r for r in rows if r["url"] == url}
        served = self.served.setdefault(url, ServedOnce())
        picked = served.pick(now, ((datetime.fromisoformat(r["fetched_at"]), p) for p, r in copies.items()))
        return copies[picked[1]] if picked else None
