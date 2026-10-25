"""The evening's release check (story FL1-1d-2; orchestrator, 22 Oct): read-only, run inside the evening routine
only (no schedule of its own, A8's workflow untouched), it records when NSE's evening files the edition reads were
out, so the edition's minute can be re-proposed from evidence after 10 sessions.
- The F&O bhavcopy: A8's own `ReleaseTimeRecorder` (NSE's Last-Modified for the bytes, `rewritten` when they change).
- FII and DII cash: NSE's API always answers with its latest day and says no time, so a check is `present` only when
  the answer names the session itself, `absent` otherwise; our own check time is the evidence.
Participant OI is not checked here: A8's watch job already measures it (one builder per function).
Each log is append-only, in A8's release-log format, beside the others under `research/data/forecast_lab/release/`."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date, datetime

from ..constants import RELEASE_ABSENT, RELEASE_PRESENT, RELEASE_UNREACHABLE
from ..models import IST, now_ist
from ..research_data.release_times import ReleaseCheck, ReleaseLog
from ..storage.raw_source import RawFileSource, RawSourceUnavailable

LINE = "release check {name} {day}: {outcome}{written}"
NSE_DAY = "%d-%b-%Y"


class FlowsRelease:
    """FII and DII cash for a session: out only when NSE's answer names that session."""

    def __init__(self, source: RawFileSource, path_for: Callable[[date], str], log: ReleaseLog,
                 clock: Callable[[], datetime] = now_ist):  # fmt: skip
        self.source, self.path_for, self.log, self.clock = source, path_for, log, clock

    def check(self, day: date) -> ReleaseCheck:
        started = self.clock()
        try:
            found = self.source.fetch_published(self.path_for(day))
        except RawSourceUnavailable:
            check = ReleaseCheck(day, self.clock(), RELEASE_UNREACHABLE, started_at=started)
        else:
            names = _days(found.data) if found is not None else set()
            outcome = RELEASE_PRESENT if day in names else RELEASE_ABSENT
            sha = hashlib.sha256(found.data).hexdigest() if outcome == RELEASE_PRESENT else ""
            check = ReleaseCheck(day, self.clock(), outcome, sha, None, started)
        self.log.append(check)
        return check


def _days(data: bytes) -> set[date]:
    try:
        rows = json.loads(data)
        return {datetime.strptime(r["date"], NSE_DAY).date() for r in rows if isinstance(r, dict) and "date" in r}
    except (ValueError, TypeError):
        return set()


class ReleaseChecks:
    def __init__(self, checks: dict[str, object]):
        """`checks`: name -> a recorder with `check(day)` (A8's `ReleaseTimeRecorder` or `FlowsRelease`)."""
        self.checks = checks

    def run(self, day: date) -> list[str]:
        lines = []
        for name, recorder in self.checks.items():
            check = recorder.check(day)
            moment = check.last_modified.astimezone(IST) if check.last_modified else None
            written = f" (last written {moment:%H:%M} IST)" if moment else ""
            lines.append(LINE.format(name=name, day=day, outcome=check.outcome, written=written))
        return lines
