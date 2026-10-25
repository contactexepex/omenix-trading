"""Takes the 15-minute snapshots of a session (story A16) and keeps the books on them: raw document to the store,
one ledger row per due mark (a mark nobody took becomes `missed`, never filled), the alert after two bad marks in a
row, the heartbeat, the session's realised variance once its last mark is settled, and the commit of the repository
files. Knows no broker: the source, store, clock servers, alerts and publisher are interfaces.

Which day is a session comes only from NSE's calendar (A7): regular and special sessions are recorded, a muhurat-only
day is not (as A4); a day outside the calendar raises `CalendarError` (the command stops loudly)."""

from __future__ import annotations

import time as clock
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from fno.ingestion.intraday.claims import LOST, UNCLAIMED, ClaimResult, MarkClaims, NoClaims
from fno.ingestion.intraday.clock import ClockCheck
from fno.ingestion.intraday.document import SnapshotDocument, utc_text
from fno.ingestion.intraday.heartbeat import Heartbeat
from fno.ingestion.intraday.ledger import SlotLedger
from fno.ingestion.intraday.observer import MarkObserver, NoObserver, notify
from fno.ingestion.intraday.session_rv import SessionRv, previous_recorded_session
from fno.ingestion.intraday.settle import Settlement
from fno.ingestion.intraday.slots import MAX_WAIT, label, marks, takeable_marks, window_end
from fno.ingestion.intraday.snapshot_files import SnapshotFiles
from fno.ingestion.intraday.source import IntradayQuoteSource
from fno.ingestion.intraday.status import FAILED
from fno.ingestion.intraday.sync import LedgerSync
from fno.ingestion.quotes.recorder import MUHURAT_ONLY, RECORDED_SESSION_KINDS
from fno.ingestion.research_data.calendar import CalendarError, SessionCalendar
from fno.shared.alerts.sender import AlertSender
from fno.shared.constants import SESSION_MUHURAT
from fno.shared.models import IST, now_ist

NOT_TRADING_DAY, ALREADY, NO_MARK, MISSED_NOW = "not a trading day", "already recorded", "no mark now", "missed"
NO_MARK_DETAIL = "no mark open or due within 15 minutes"
LATE_START = "the mark's 120 s window closed before the index request could go out"
TAKEN_DETAIL = (
    "{recorded_contracts} of {expected_contracts} contracts ({two_sided_contracts} two-sided), index answered "
    "{lateness_seconds} s after the mark; failures: {failures}"
)

TAKE_FAILED, DRIVE_WRITE = "take", "drive_write"
CLAIM_LEAD, CLAIM_RETRY = timedelta(seconds=45), timedelta(seconds=15)
CLAIMED_BY = "claimed by another run ({run}): taken there, not here"
NOT_CLAIMED = (
    "claim not pushed ({detail}): not taken here, as another run may hold it unseen and two takers exceed Groww's "
    "limit (GW1); a run whose claim landed takes it"
)
CLAIM_LINE = "claim {outcome}: {detail}"
STARTED_AFTER = "started after --until {until:%H:%M}: nothing to take"
ALREADY_PAUSE_SECONDS = 60
HEARTBEAT_NAME = "story A16 intraday recorder"
PREVIOUS_UNSETTLED = "previous session not settled: the calendar cannot answer ({reason})"
RV_FAILED = (
    "Action: check the 15-minute recorder's realised variance for {day} (story A16). SYSTEM: it was NOT written "
    "({reason}); the slot rows and raw snapshots are kept."
)
GOOD_OUTCOMES = ("good", ALREADY, NOT_TRADING_DAY, NO_MARK)


class SettleRefused(ValueError):
    """`rv` was asked for a day that is not a recorded session, or has not finished."""


@dataclass
class SlotOutcome:
    status: str
    mark: str = ""
    detail: str = ""
    lines: list[str] = field(default_factory=list)  # alert outcomes, clock warning, realised variance, commit

    def summary(self) -> str:
        head = f"{self.mark} {self.status}" if self.mark else self.status
        return f"{head}: {self.detail}" if self.detail else head


class IntradayRecorder:
    def __init__(self, source: IntradayQuoteSource, files: SnapshotFiles, ledger: SlotLedger, heartbeat: Heartbeat,
                 calendar: SessionCalendar, alerts: AlertSender, clock_check: ClockCheck, session_rv: SessionRv,
                 sync: LedgerSync, now: Callable[[], datetime] = now_ist, sleep=clock.sleep,
                 claims: MarkClaims | None = None, observer: MarkObserver | None = None):  # fmt: skip
        self.source, self.files, self.ledger, self.heartbeat = source, files, ledger, heartbeat
        self.calendar, self.alerts, self.clock_check, self.session_rv = calendar, alerts, clock_check, session_rv
        self.sync, self.now, self.sleep, self.claims = sync, now, sleep, claims or NoClaims()
        self.observer = observer or NoObserver()
        self.settlement = Settlement(files, ledger, alerts)
        self._lost: set[datetime] = set()  # marks another run claimed: never taken by this run

    def snapshot(self, until: time | None = None) -> SlotOutcome:
        """Takes the next open or coming mark (waiting at most 15 minutes), unless it is after `until`. Never stops
        on a source or store failure: the mark gets a `failed` row, the streak rule and the heartbeat still run."""
        started = self.now()
        day = started.astimezone(IST).date()
        kind = self.calendar.session_kind(day)
        if kind not in RECORDED_SESSION_KINDS:
            return SlotOutcome(NOT_TRADING_DAY, detail=MUHURAT_ONLY if kind == SESSION_MUHURAT else "")
        lines = [self.sync.pull()] + self._settle_previous(day)  # see what an overlapping run already pushed
        open_marks = [m for m in takeable_marks(day, started) if until is None or m.time() <= until]
        settled = {row["mark"] for row in self.ledger.rows(day)}  # after the pull: also the other run's rows
        mark = next((m for m in open_marks if utc_text(m) not in settled and m not in self._lost), None)
        if mark is None:
            status, detail = (ALREADY, "") if open_marks else (NO_MARK, NO_MARK_DETAIL)
            outcome = SlotOutcome(status, label(open_marks[0]) if open_marks else "", detail, lines)
            return self._close(day, started, outcome)
        self.source.prepare(day)
        claim = self._claim(day, mark)
        if not claim.take:
            self._lost.add(mark)
            return self._close(day, started, _not_taken(mark, claim, lines))
        lines += [CLAIM_LINE.format(outcome=claim.outcome, detail=claim.detail)] if claim.detail else []
        wait = (mark - self.now()).total_seconds()
        if wait > 0:
            self.sleep(wait)
        if self.now() > window_end(mark):
            return self._close(day, started, SlotOutcome(MISSED_NOW, label(mark), LATE_START, lines))
        taken = self._take(day, mark)
        if isinstance(taken, str):
            return self._close(day, started, SlotOutcome(FAILED, label(mark), taken, lines), failed=(mark, taken))
        warning = taken[2].warning()
        return self._close(day, started, SlotOutcome("", label(mark), lines=lines + ([warning] if warning else [])),
                           taken)  # fmt: skip

    def run(self, until: time) -> list[SlotOutcome]:
        """The session loop: every mark up to `until` (IST), each waited for; stops on a day not recorded."""
        if self.now().astimezone(IST).time() >= until:
            return [SlotOutcome(NO_MARK, detail=STARTED_AFTER.format(until=until))]
        outcomes = []
        while self.now().astimezone(IST).time() < until:
            outcome = self.snapshot(until)
            outcomes.append(outcome)
            if outcome.status == NOT_TRADING_DAY or not self._later_mark(until):
                break
            if outcome.status == NO_MARK:  # started more than MAX_WAIT early (the 08:52 fire): wait, never end
                self._wait_for_next_mark(until)
            if outcome.status == ALREADY:  # another host took the open marks: wait for the next one to open
                self.sleep(ALREADY_PAUSE_SECONDS)
        return outcomes

    def settle_day(self, day: date | None = None) -> list[str]:
        """The `rv` command: the missed rows of a finished recorded session (default: the latest) and its realised
        variance, committed. Refuses a day that is not a recorded session or has not finished."""
        day = day or self._latest_finished(self.now())
        if self.calendar.session_kind(day) not in RECORDED_SESSION_KINDS:
            raise SettleRefused(f"{day} is not a recorded session")
        if self.now() <= window_end(marks(day)[-1]):
            raise SettleRefused(f"{day} has not finished (its 15:30 mark's window is still open or ahead)")
        lines = [self.sync.pull()] + self._settle_finished(day)
        return lines + [self.sync.commit(f"{day} settled")]

    def _settle_finished(self, day: date) -> list[str]:
        rows, alert = self.settlement.settle(day, self.now())
        return ([alert] if alert else []) + notify(self.observer, day, rows, None) + self._finish_session(day)

    def _settle_previous(self, day: date) -> list[str]:
        """A previous session the host left unfinished (it died mid-session or missed the whole day) gets its missed
        rows and its realised variance on the next session's first run, so no day waits for someone to run `rv` by
        hand. Only once the recorder has a history: the day before its first session was never due."""
        try:
            previous = previous_recorded_session(self.calendar, day)
        except CalendarError as error:
            return [PREVIOUS_UNSETTLED.format(reason=type(error).__name__)]
        if not self.ledger.sessions_before(day):
            return []  # the recorder's first session: nothing before it was ever due
        if len(self.ledger.rows(previous)) == len(marks(previous)) and self.session_rv.has_row(previous):
            return []
        return self._settle_finished(previous)

    def _latest_finished(self, now: datetime) -> date:
        today = now.astimezone(IST).date()
        if self.calendar.session_kind(today) in RECORDED_SESSION_KINDS and now > window_end(marks(today)[-1]):
            return today
        return previous_recorded_session(self.calendar, today)

    def _claim(self, day: date, mark: datetime) -> ClaimResult:
        """Claims the mark CLAIM_LEAD before it: late enough that a run dying while it waits rarely holds a mark it
        never takes, early enough for a push to land. A claim that did not reach GitHub is tried once more
        CLAIM_RETRY later (a network blip), still before the mark (GW1: an unclaimed mark is not taken)."""
        wait = (mark - CLAIM_LEAD - self.now()).total_seconds()
        if wait > 0:
            self.sleep(wait)
        claim = self.claims.claim(day, mark)
        if claim.outcome != UNCLAIMED:
            return claim
        self.sleep(CLAIM_RETRY.total_seconds())
        return self.claims.claim(day, mark)

    def _later_mark(self, until: time) -> bool:
        return self._next_mark(until) is not None

    def _next_mark(self, until: time) -> datetime | None:
        now = self.now()
        return next((m for m in marks(now.astimezone(IST).date()) if m > now and m.time() <= until), None)

    def _wait_for_next_mark(self, until: time) -> None:
        """Sleeps until the next mark is within MAX_WAIT, so the next snapshot takes it."""
        wait = (self._next_mark(until) - MAX_WAIT - self.now()).total_seconds()
        if wait > 0:
            self.sleep(wait)

    def _take(self, day: date, mark: datetime):
        """(document, bytes, clock reading, Drive path) of this run's copy, saved under its own name; else the
        failure's name. A failed Drive write drops the document: it is never written to the repository or spooled in
        the checkout."""
        try:
            data = self.source.take(day, mark).to_bytes()
        except Exception as exc:  # the class name only: an exception's text could carry a credential
            return f"{TAKE_FAILED}: {type(exc).__name__}"
        try:
            path = self.files.save(day, mark, data)
        except Exception as exc:
            return f"{DRIVE_WRITE}: {type(exc).__name__}"
        return SnapshotDocument.from_bytes(data), data, self.clock_check.check(), path

    def _close(self, day: date, started: datetime, outcome: SlotOutcome, taken=None, failed=None) -> SlotOutcome:
        """Settles the ledger and alerts, writes the heartbeat, the realised variance once the session is complete,
        and commits. A realised-variance error is reported and alerted, never allowed to stop the rest."""
        rows, alert = self.settlement.settle(day, self.now(), taken, failed)
        outcome.lines += ([alert] if alert else []) + notify(self.observer, day, rows, taken[0] if taken else None)
        mine = next((r for r in rows if r["mark_ist"] == outcome.mark), None)
        if taken is not None and mine is not None:
            outcome.status, outcome.detail = mine["status"], TAKEN_DETAIL.format(**mine)
        self._beat(day, started, outcome, taken if taken else None, took=taken is not None or failed is not None)
        if len(self.ledger.rows(day)) == len(marks(day)):
            outcome.lines += self._finish_session(day)
        outcome.lines.append(self.sync.commit(f"{day} {outcome.mark or outcome.status}"))
        return outcome

    def _beat(self, day: date, started: datetime, outcome: SlotOutcome, taken, took: bool) -> None:
        """The heartbeat: run times always; the last mark's fields only when this run took or failed a mark."""
        beat = (self.heartbeat.read() or {}) if not took else {}
        beat.update(recorder=HEARTBEAT_NAME, run_started_at=utc_text(started), run_finished_at=utc_text(self.now()))
        if took:
            beat.update(session=day.isoformat(), mark=outcome.mark, status=outcome.status,
                        clock_status=taken[2].status if taken else "",
                        clock_skew_seconds=taken[2].worst if taken else None)  # fmt: skip
        self.heartbeat.write(beat)

    def _finish_session(self, day: date) -> list[str]:
        try:
            return [self.session_rv.compute(day), self.session_rv.void_share_line()]
        except Exception as exc:  # e.g. RvConflict: loud, alerted, and the commit still happens
            line = RV_FAILED.format(day=day, reason=type(exc).__name__)
            return [line, self.alerts.send(line)]


def _not_taken(mark: datetime, claim: ClaimResult, lines: list[str]) -> SlotOutcome:
    if claim.outcome == LOST:
        return SlotOutcome(ALREADY, label(mark), CLAIMED_BY.format(run=claim.holder), lines)
    return SlotOutcome(MISSED_NOW, label(mark), NOT_CLAIMED.format(detail=claim.detail), lines)
