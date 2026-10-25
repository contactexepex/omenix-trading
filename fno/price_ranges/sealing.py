"""Sealing (part A5): a live record counts only when its receipt reached `origin/main` by the issue's deadline, by
GitHub's own push time (O8's `Evidence.file_pushed_at`, GitHub's activity log), never a commit date. Push evidence
that is unavailable means `late`, never assumed sealed.

Story receipts-reach: a seal is final only on an answer. A known push time is final (on time or late); so is a log
that no longer reaches the push (`OUTSIDE_LOG`), and no push found once the deadline has passed (any later push is
late). A failed read (network, HTTP, git, or any error not one of those answers) is retried within the run and then
left open, `waiting` UNAVAILABLE, for a later run; a file not committed yet, or not pushed before its deadline, is
left open as NOT_YET."""

from __future__ import annotations

import time as clock
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from ..health.model import EvidenceNotCommitted, EvidenceNotPushed, EvidenceOutsideLog
from ..models import IST, now_ist
from ..price_distribution.horizons import nth_regular_session
from ..research_data.calendar import CalendarError, SessionCalendar
from .constants import DEADLINE

NO_EVIDENCE = "late: push time unknown ({why})"
PAST_DEADLINE = "late: pushed {pushed} after the deadline {deadline}"
OUTSIDE_LOG = "late: GitHub's activity log no longer reaches its push ({why})"
NOT_PUSHED = "late: no push of it by the deadline {deadline} ({why})"
UNAVAILABLE, NOT_YET = "evidence unavailable", "not pushed yet"
RETRY_SECONDS = 10
ANSWERS = (EvidenceOutsideLog, EvidenceNotCommitted, EvidenceNotPushed)  # what GitHub and git said, not a failure


def next_session_0915(calendar: SessionCalendar, day: date) -> datetime:
    """09:15 IST of the next regular session (a 15:45 issue)."""
    return datetime.combine(nth_regular_session(calendar, day, 1), DEADLINE, IST)


@dataclass(frozen=True)
class Seal:
    sealed_at: datetime | None
    deadline: datetime | None
    late: bool
    reason: str | None = None
    waiting: str | None = None  # None: final; else why it is still open (UNAVAILABLE or NOT_YET), never stored


class SealCheck:
    def __init__(self, pushed_at: Callable[[str], datetime], calendar: SessionCalendar,
                 deadline_of: Callable[[SessionCalendar, date], datetime] | None = None,
                 now: Callable[[], datetime] = now_ist, attempts: int = 1,
                 pause: Callable[[float], None] = clock.sleep):  # fmt: skip
        """`pushed_at(repository path)`: GitHub's receipt time of the commit that first added the file; raises when
        unknown. `deadline_of(calendar, day)`: the issue's deadline (default: a 15:45 issue's, `next_session_0915`);
        G13d passes its own. `attempts`: reads of a failed evidence read within one run (the wiring sets them)."""
        self.pushed_at, self.calendar, self.deadline_of = pushed_at, calendar, deadline_of or next_session_0915
        self.now, self.attempts, self.pause = now, attempts, pause

    def deadline(self, day: date) -> datetime | None:
        try:
            return self.deadline_of(self.calendar, day)
        except CalendarError:
            return None

    def seal(self, receipt_path: str, day: date) -> Seal:
        deadline = self.deadline(day)
        try:
            pushed = self._pushed_at(receipt_path)
        except EvidenceOutsideLog as outside:
            return Seal(None, deadline, True, OUTSIDE_LOG.format(why=outside))
        except (EvidenceNotCommitted, EvidenceNotPushed) as missing:
            if isinstance(missing, EvidenceNotPushed) and deadline is not None and self.now() > deadline:
                return Seal(None, deadline, True, NOT_PUSHED.format(deadline=deadline, why=missing))
            return Seal(None, deadline, True, NO_EVIDENCE.format(why=missing), NOT_YET)
        except Exception as error:  # noqa: BLE001 - a failed read is open, never "sealed" and never a final "late"
            return Seal(None, deadline, True, NO_EVIDENCE.format(why=f"{type(error).__name__}: {error}"), UNAVAILABLE)
        if deadline is None or pushed > deadline:
            return Seal(pushed, deadline, True, PAST_DEADLINE.format(pushed=pushed, deadline=deadline))
        return Seal(pushed, deadline, False)

    def _pushed_at(self, receipt_path: str) -> datetime:
        """Reads again after a failed read (not after an answer), up to `attempts` reads, RETRY_SECONDS apart."""
        for _ in range(self.attempts - 1):
            try:
                return self.pushed_at(receipt_path)
            except ANSWERS:
                raise
            except Exception:  # noqa: BLE001 - a failed read: the last attempt below raises it
                self.pause(RETRY_SECONDS)
        return self.pushed_at(receipt_path)
