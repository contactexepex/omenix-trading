"""The paper desk's daily run (E3) and A16's 15-minute marks.

- Desk: `journal/runs/<date>.json` holds every step of `DAILY_RUN_STEPS` (story O1's tuple, the one the run loops
  over); the `decisions` step started within E3's own collection rule, the timetable's decision deadline plus
  `COLLECTION_GRACE` (its in-file start time: E3 records what was visible at that start and fails closed after it, so
  its finish, a second later, is not the measure; the O1 dry run, 23 Oct); an O1 step whose status
  is `failed` or `refused` is a problem shown with its reason, `not_live` is present and counts as neither; a `skipped`
  run (not a session day) is not expected.
- A16: the day's ledger has every mark with status `good`. A16's own per-mark status (its 120 s rule) is final: this
  check only counts it, with no deadline of its own beyond the session's last mark."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ..constants import (
    DAILY_RUN_STEPS,
    HEALTH_LATE,
    HEALTH_MISSED,
    HEALTH_NOT_EXPECTED,
    HEALTH_OK,
    NO_DECISION_LATE,
    RUN_LOG_DECISIONS_STEP,
    STEP_FAILED,
    STEP_REFUSED,
)
from ..desk.daily_steps import COLLECTED_LATE, COLLECTION_GRACE
from ..desk.run_log import RunLog
from ..intraday.ledger import SlotLedger
from ..intraday.slots import FIRST_MARK, MARK_STEP, MARKS_PER_SESSION
from ..intraday.status import GOOD, LATE
from ..models import IST
from .model import CheckResult, Deadline, EvidenceUnknown, SessionCheck, absent, judged

SKIPPED_STEP = "skipped"  # the run's closed-day step
E3_LATE = "E3 collected late: {reason}"
INCONSISTENT = "run log inconsistent: COLLECTED_LATE on some books only ({reason})"


class RunLogCheck(SessionCheck):
    def __init__(self, root: Path, deadline: Deadline):
        self.root, self.deadline = Path(root), deadline

    def check(self, session: date, now: datetime) -> CheckResult:
        log = RunLog.open(self.root, session)
        if not log.steps:
            return absent(now, self.deadline.on(session), "never ran: no run log")
        if log.done(SKIPPED_STEP):
            return CheckResult(HEALTH_NOT_EXPECTED, "run skipped: not a session day")
        due = self.deadline.on(session) + COLLECTION_GRACE
        if not log.done(RUN_LOG_DECISIONS_STEP):
            return absent(now, due, "no decisions step")
        late = _collected_late(log.steps[RUN_LOG_DECISIONS_STEP])
        if late:
            return CheckResult(HEALTH_LATE, late)  # E3's own verdict, the one source of truth
        try:
            started = datetime.fromisoformat(log.steps[RUN_LOG_DECISIONS_STEP]["started_at"])
        except (KeyError, TypeError, ValueError):
            raise EvidenceUnknown(f"{log.path.name}: the decisions step has no readable start time") from None
        result = judged(started, due, "decisions collected")
        problems = _problems(log)
        if result.status == HEALTH_OK and problems:
            return CheckResult(HEALTH_MISSED, problems)
        return result


def _collected_late(step: dict) -> str:
    """The late-collection line when E3 started after its grace and failed closed; empty otherwise. E3 writes its
    `COLLECTED_LATE` reason in one place (`_all_late`), for every book at once from the step's one start time, so one
    book carrying it is enough. On some books only it cannot come from E3: the run log was edited or broken, and the
    line says so. It wins over the start time, which the run log takes a few ms before E3's own clock."""
    prefix = COLLECTED_LATE.split("{", 1)[0]
    books = [b for b in (step.get("result") or {}).values() if isinstance(b, dict)]
    late = [b["reason"] for b in books if b.get("decision") == NO_DECISION_LATE and _starts(b.get("reason"), prefix)]
    if not late:
        return ""
    return (INCONSISTENT if len(late) < len(books) else E3_LATE).format(reason=late[0])


def _starts(text, prefix: str) -> bool:
    return isinstance(text, str) and text.startswith(prefix)


def _problems(log: RunLog) -> str:
    """Steps not run, and O1 steps that failed or were refused with their reasons; empty when there are none."""
    missing = [step for step in DAILY_RUN_STEPS if step not in log.steps]  # a failed step awaiting its retry ran
    results = {name: step["result"] for name, step in log.steps.items()}
    bad = [f"{name} {r['status']}: {r.get('reason', '')}" for name, r in results.items()
           if r.get("status") in (STEP_FAILED, STEP_REFUSED)]  # fmt: skip
    parts = ([f"steps not run: {', '.join(missing)}"] if missing else []) + (
        [f"steps not ok: {'; '.join(bad)}"] if bad else []
    )
    return "; ".join(parts)


class MarksCheck(SessionCheck):
    def __init__(self, folder: Path):
        self.ledger = SlotLedger(folder)

    def check(self, session: date, now: datetime) -> CheckResult:
        last_mark = datetime.combine(session, FIRST_MARK, IST) + MARK_STEP * (MARKS_PER_SESSION - 1)
        rows = self.ledger.rows(session)
        if not rows:
            return absent(now, last_mark, "no marks")
        good = sum(1 for row in rows if row.get("status") == GOOD)
        late = sum(1 for row in rows if row.get("status") == LATE)
        if good == MARKS_PER_SESSION:
            return CheckResult(HEALTH_OK, f"{good} of {MARKS_PER_SESSION} good")
        detail = f"{good} of {MARKS_PER_SESSION} good, {late} late, {MARKS_PER_SESSION - good - late} other"
        if now < last_mark:
            return absent(now, last_mark, detail)
        return CheckResult(HEALTH_LATE if good + late == MARKS_PER_SESSION else HEALTH_MISSED, detail)
