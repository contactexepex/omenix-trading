"""What one check of one session found, and the rules every check shares: a deadline is a time on the session day or a
later day; "late" is decided by one time per row (a GitHub push receipt or a time written in the file, the story's
table); a file that is absent is `not due` before its deadline and `missed` after it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from ..constants import HEALTH_LATE, HEALTH_MISSED, HEALTH_NOT_DUE, HEALTH_OK
from ..models import IST


class EvidenceUnknown(RuntimeError):
    """A file could not be read or its push time could not be established: the check's status is `unknown`."""


class EvidenceNotCommitted(EvidenceUnknown):
    """No commit in this checkout adds the file."""


class EvidenceNotPushed(EvidenceUnknown):
    """GitHub's log covers every moment the file's commit could have been pushed, and holds no push of it."""


class EvidenceOutsideLog(EvidenceUnknown):
    """GitHub's log no longer reaches back to when the file's commit could have been pushed."""


@dataclass(frozen=True)
class Deadline:
    at: time
    days_after: int = 0  # 1: the next calendar day (the evening jobs' retries)

    def on(self, session: date) -> datetime:
        return datetime.combine(session + timedelta(days=self.days_after), self.at, IST)


@dataclass(frozen=True)
class CheckResult:
    status: str
    detail: str = ""


class SessionCheck(ABC):
    @abstractmethod
    def check(self, session: date, now: datetime) -> CheckResult:
        """This check's status for one session, as seen at `now`. Raises EvidenceUnknown when it cannot tell."""


def judged(when: datetime, deadline: datetime, what: str) -> CheckResult:
    """On time at or before the deadline; one second after it is late."""
    shown = when.astimezone(IST)
    if when <= deadline:
        return CheckResult(HEALTH_OK, f"{what} {shown:%H:%M:%S}")
    return CheckResult(HEALTH_LATE, f"{what} {shown:%d %b %H:%M:%S}, due {deadline:%d %b %H:%M}")


def absent(now: datetime, deadline: datetime, reason: str) -> CheckResult:
    return CheckResult(HEALTH_NOT_DUE if now < deadline else HEALTH_MISSED, reason)
