"""The evening data jobs: the session's row (or the panel's day) is committed, and GitHub received the commit that first
added it by the job's deadline. These deadlines have no owner elsewhere in `fno/`: they live in `expectations.py`."""

from __future__ import annotations

from datetime import date, datetime

from ..constants import HEALTH_MISSED
from .evidence import Evidence
from .model import CheckResult, Deadline, SessionCheck, absent, judged


class SessionRowCheck(SessionCheck):
    """A CSV whose first column is the session date (participant OI, index closes, FII/DII flows)."""

    def __init__(self, evidence: Evidence, path: str, deadline: Deadline):
        self.evidence, self.path, self.deadline = evidence, path, deadline

    def check(self, session: date, now: datetime) -> CheckResult:
        key = f"{session.isoformat()},"
        text = self.evidence.text(self.path) or ""
        if not any(line.startswith(key) for line in text.splitlines()):
            return absent(now, self.deadline.on(session), f"no row in {self.path.rsplit('/', 1)[1]}")
        return judged(self.evidence.row_pushed_at(self.path, key, session), self.deadline.on(session), "pushed")


class PanelDayCheck(SessionCheck):
    """The NIFTY panel's manifest: the session is among its days, with status ok."""

    def __init__(self, evidence: Evidence, path: str, deadline: Deadline):
        self.evidence, self.path, self.deadline = evidence, path, deadline

    def check(self, session: date, now: datetime) -> CheckResult:
        day = ((self.evidence.json(self.path) or {}).get("days") or {}).get(session.isoformat())
        if day is None:
            return absent(now, self.deadline.on(session), "not in the panel")
        if day.get("status") != "ok":
            return CheckResult(HEALTH_MISSED, f"panel status {day.get('status')}")
        pushed = self.evidence.row_pushed_at(self.path, f'"{session.isoformat()}": {{', session)
        return judged(pushed, self.deadline.on(session), "pushed")
