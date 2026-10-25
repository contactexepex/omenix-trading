"""Protocol v4's 15:10 deadline, checked live (story G10 completion, criterion 7): for each scored session from the live
date to today without a verdict, every live commitment's GitHub receipt time (never a commit's own time), one verdict
file written once in Drive, `v4/deadlines/<YYYY>/<date>.json`. Any unknown receipt time writes nothing for that day
(never a guessed time): the run fails and the next run retries it. Today is checked only from 15:12 IST, once the
pushes up to 15:10 can be in GitHub's log."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time

from ..models import IST
from ..storage.data_store import DataStore
from ..storage.raw_store import RawFileConflict
from .commitment import CommitmentTimes, CommitmentTimeUnknown, on_time
from .commitments import ROW, Commitment, CommitmentSource
from .paths import deadline_path

CHECK_FROM = time(15, 12)
ON_TIME, LATE = "on_time", "late"
NOT_LIVE = "v4 deadline: not live (config.yaml daily.live_from.v4_pack is not set or is later)"
TOO_EARLY = "v4 deadline {day}: not checked before {at:%H:%M}"
CHECKED = "v4 deadline {day}: {on_time} on time, {late} late"
UNKNOWN = "v4 deadline {day}: NOT checked ({error}); the next run retries it"
REFUSED = "v4 deadline {day}: REFUSED by the write-once store ({error}); nothing overwritten"


@dataclass(frozen=True)
class Verdict:
    forecaster: str
    question: str
    received_at: datetime
    verdict: str


def verdict_bytes(day: date, verdicts: list[Verdict]) -> bytes:
    body = {"day": day.isoformat(), "commitments": [
        {"forecaster": v.forecaster, "question": v.question, "received_at": v.received_at.isoformat(),
         "verdict": v.verdict} for v in verdicts]}  # fmt: skip
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def parse_verdicts(data: bytes) -> tuple[date, dict[tuple[str, str], str]]:
    """The day and each (forecaster, question)'s verdict; a broken file raises ValueError."""
    body = json.loads(data.decode("utf-8"))
    found = {(c["forecaster"], c["question"]): c["verdict"] for c in body["commitments"]}
    if not set(found.values()) <= {ON_TIME, LATE}:
        raise ValueError(f"{body['day']}: a verdict other than {ON_TIME} or {LATE}")
    return date.fromisoformat(body["day"]), found


class DeadlineRun:
    def __init__(self, store: DataStore, in_drive: Callable[[str], bool], source: CommitmentSource,
                 times: CommitmentTimes, sessions: Callable[[date, date], list[date]], live_from: date | None,
                 clock: Callable[[], datetime], catch_up: bool = True, checks_from: date | None = None):  # fmt: skip
        """`live_from`: the check's own live date (`daily.live_from.v4_pack`); `checks_from`: the first live v4 session
        the catch-up checks (`daily.live_from.forecasts_v4`, as the release's catch-up; default `live_from`);
        `catch_up=False` checks today only (a rehearsal: its push log holds only its own pushes)."""
        self.store, self.in_drive, self.source, self.times = store, in_drive, source, times
        self.sessions, self.live_from, self.clock, self.catch_up = sessions, live_from, clock, catch_up
        self.checks_from = checks_from or live_from
        self.failed = False

    def run(self, today: date) -> list[str]:
        if self.live_from is None or today < self.live_from:
            return [NOT_LIVE]
        first = self.checks_from if self.catch_up else today
        days = [d for d in self.sessions(first, today) if not self._checked(d)]
        return [self._check(day, today) for day in days]

    def _check(self, day: date, today: date) -> str:
        at = datetime.combine(day, CHECK_FROM, IST)
        if day == today and self.clock() < at:
            return TOO_EARLY.format(day=day, at=at)
        try:
            verdicts = [self._verdict(c, day) for c in self.source.commitments(day)]
        except CommitmentTimeUnknown as unknown:
            self.failed = True
            return UNKNOWN.format(day=day, error=unknown)
        try:
            self.store.put(deadline_path(day), verdict_bytes(day, verdicts))
        except RawFileConflict as error:
            self.failed = True
            return REFUSED.format(day=day, error=type(error).__name__)
        late = sum(v.verdict == LATE for v in verdicts)
        return CHECKED.format(day=day, on_time=len(verdicts) - late, late=late)

    def _verdict(self, commitment: Commitment, day: date) -> Verdict:
        if commitment.kind == ROW:
            received = self.times.row_received_at(commitment.path, commitment.text, day)
        else:
            received = self.times.file_received_at(commitment.path)
        return Verdict(
            commitment.forecaster, commitment.question, received, ON_TIME if on_time(received, day) else LATE
        )

    def _checked(self, day: date) -> bool:
        return self.in_drive(f"{self.store.area}/{deadline_path(day)}")
