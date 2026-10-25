"""The candle back-fill (story A16b): Groww's 15-minute windows of up to 90 days, each session's 1-minute check, NSE's
day and one row per recorded session, in calendar order.

- Raw first: each answer is archived in Drive with its manifest row before any row is derived from it.
- Transient (a call or read failed: Groww, Drive or NSE) defers the session: no row, named, exit 1, retried next run.
  Permanent (an answer received, the data absent) writes a void row (`session_deriver.py`).
- A session is written only when its previous recorded session has a row (else it is deferred), so a failed window
  never fixes a wrong overnight figure in place.
- Three Groww failures in a row stop the run rather than press a refusing service.
- Read-only towards Groww; never touches A16's files."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from ..models import IST
from ..quotes.recorder import RECORDED_SESSION_KINDS
from ..research_data.calendar import SessionCalendar
from ..storage.raw_store import RawFileConflict, StoredCopyDamaged
from .candle_archive import ArchivedCopy, CandleArchive
from .candle_levels import CANDLES_PER_SESSION, CandleParse, parse_candles
from .candle_rv_table import CandleRvTable
from .candle_source import FIFTEEN_MINUTES, CandleCallFailed, IntradayCandleSource
from .deferral_log import DeferralLog
from .nse_days import NseDays, NseReadFailed
from .previous_close import PreviousClose
from .session_deriver import SessionDeriver, SessionInputs
from .session_rv import previous_recorded_session

SERIES_START = date(2020, 1, 1)  # Groww's 15-minute index history starts here (step 0)
WINDOW_DAYS = 90
FAILURES_TO_STOP = 3
STORE_FAILURES = (RawFileConflict, StoredCopyDamaged, OSError, RuntimeError, ValueError, KeyError)  # incl. CopyDamaged
NSE_FINAL_DAYS, NSE_FINAL_AT = (
    1,
    time(21, 0),
)  # NSE's file is archived by 21:00 IST (A13); a day's grace before 404 counts
NO_PREVIOUS_ROW = "previous session {day} has no row"
NOT_PUBLISHED = "NSE index-close {day}: not published yet (a 404 counts as absent from {final:%Y-%m-%d %H:%M} IST)"
CHANGED = "{day}: a later 15-minute answer differs from the first copy {path}; the row keeps the first"


class BackfillStopped(RuntimeError):
    """Groww failed several times in a row: the run stopped; what it wrote stays."""


@dataclass
class BackfillReport:
    sessions: list[date] = field(default_factory=list)
    written: dict[date, dict] = field(default_factory=dict)
    held: int = 0  # sessions that already had a row
    deferred: dict[date, str] = field(default_factory=dict)
    windows: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)  # sessions whose later answer differs from the copy kept
    stopped: str = ""

    @property
    def complete(self) -> bool:
        return not self.deferred and not self.stopped


def recorded_sessions(calendar: SessionCalendar, start: date, end: date) -> list[date]:
    return [d for d in calendar.sessions(start, end) if calendar.session_kind(d) in RECORDED_SESSION_KINDS]


def first_recorded_session(calendar: SessionCalendar, series_start: date) -> date | None:
    """The series' first session: it has no previous close (a void overnight part)."""
    return next(iter(recorded_sessions(calendar, series_start, series_start + timedelta(days=14))), None)


def nse_final(day: date) -> datetime:
    """From when NSE's 404 for `day` means the file will not come (before it, the file may simply be late)."""
    return datetime.combine(day + timedelta(days=NSE_FINAL_DAYS), NSE_FINAL_AT, tzinfo=IST)


class CandleBackfill:
    def __init__(
        self,
        source: IntradayCandleSource,
        archive: CandleArchive,
        nse: NseDays,
        table: CandleRvTable,
        deferrals: DeferralLog,
        deriver: SessionDeriver,
        calendar: SessionCalendar,
        clock: Callable[[], datetime],
        series_start: date = SERIES_START,
    ):
        """`series_start`: the first day of the series (its first session has no previous close)."""
        self.source, self.archive, self.nse, self.table = source, archive, nse, table
        self.series_start, self.previous = series_start, PreviousClose(archive, deriver)
        self.deferrals, self.deriver, self.calendar, self.clock = deferrals, deriver, calendar, clock
        self._failures, self._first = 0, None

    def run(self, start: date, end: date) -> BackfillReport:
        report = BackfillReport(sessions=recorded_sessions(self.calendar, max(start, self.series_start), end))
        self._first = first_recorded_session(self.calendar, self.series_start)
        try:
            for window_start, window_end in windows(report.sessions):
                self._window(window_start, window_end, report)
        except BackfillStopped as stop:
            report.stopped = str(stop)
            for day in report.sessions:
                if day not in report.written and day not in report.deferred and self.table.row(day) is None:
                    report.deferred[day] = "not reached: the run stopped"
        self.deferrals.append(self.clock(), report.deferred)
        return report

    def _window(self, start: date, end: date, report: BackfillReport) -> None:
        days = [d for d in report.sessions if start <= d <= end]
        todo = [d for d in days if self.table.row(d) is None]
        report.held += len(days) - len(todo)
        if not todo:
            report.windows.append(f"window {start}..{end}: {len(days)} sessions already derived, not fetched")
            return
        what = f"window {start}..{end}"
        fresh = self._fetch(lambda: self.source.candles(start, end), what, todo, report)
        if fresh is None:
            return
        try:
            earlier = [c for c in self.archive.copies(FIFTEEN_MINUTES, start, end) if c.path != fresh.path]
        except STORE_FAILURES as failed:
            report.deferred.update(dict.fromkeys(todo, f"{what}: an earlier copy: {type(failed).__name__}"))
            return
        found = sum(len(self.deriver.candles(d, fresh).used) for d in days)
        report.windows.append(
            f"{what}: {found} of {CANDLES_PER_SESSION * len(days)} session candles ({len(days)} sessions)"
        )
        for day in days:
            first = next((c for c in earlier if c.start <= day <= c.end), fresh)  # the first version is kept (A11)
            if first is not fresh and self.deriver.candles(day, first) != self.deriver.candles(day, fresh):
                report.changed.append(CHANGED.format(day=day, path=first.path))
            if day in todo:
                self._session(day, first, report)

    def _session(self, day: date, window: ArchivedCopy, report: BackfillReport) -> None:
        previous_close, why = self._previous_close(day, report)
        if why:
            report.deferred[day] = why
            return
        minutes = None
        if self.deriver.candles(day, window).used:  # every present level is checked (decisions 55 and 62)
            minutes = self._fetch(lambda: self.source.minute_candles(day), f"1-minute {day}", [day], report)
            if minutes is None:
                return
        try:
            nse = self.nse.read(day)
        except NseReadFailed as failed:
            report.deferred[day] = str(failed)
            return
        if nse.day is None and self.clock() < nse_final(day):
            report.deferred[day] = NOT_PUBLISHED.format(day=day, final=nse_final(day))
            return
        row = self.deriver.derive(SessionInputs(day, window, minutes, nse, previous_close))
        self.table.write_once(row)
        report.written[day] = row

    def _previous_close(self, day: date, report: BackfillReport) -> tuple[float | None, str]:
        """The previous session's 15:30 level (None at the series start or when untrusted), or why `day` must wait."""
        if day == self._first:
            return None, ""
        previous = previous_recorded_session(self.calendar, day)
        row = report.written.get(previous) or self.table.row(previous)
        if row is None:
            return None, NO_PREVIOUS_ROW.format(day=previous)
        try:
            return self.previous.of(row), ""
        except STORE_FAILURES as failed:
            return None, f"previous session {previous}: its 15-minute copy: {type(failed).__name__}"

    def _fetch(self, call, what: str, days: list[date], report: BackfillReport) -> ArchivedCopy | None:
        """The answer archived, or None with every session of `days` deferred (transient)."""
        try:
            answer = call()
            self._failures = 0
            parse_candles(answer.rows)  # an unreadable answer is transient too, and is not archived (criterion 1)
            return self.archive.save(answer)
        except CandleCallFailed as failed:
            reason = str(failed)
            self._failures += 1
        except (*STORE_FAILURES, CandleParse) as failed:
            reason = f"{what}: {type(failed).__name__}"
        report.deferred.update(dict.fromkeys(days, reason))
        if self._failures >= FAILURES_TO_STOP:
            raise BackfillStopped(f"{FAILURES_TO_STOP} Groww failures in a row, the last: {reason}")
        return None


def windows(sessions: list[date]) -> list[tuple[date, date]]:
    """Consecutive windows of at most WINDOW_DAYS calendar days covering the sessions."""
    found, index = [], 0
    while index < len(sessions):
        start = sessions[index]
        end = start + timedelta(days=WINDOW_DAYS - 1)
        found.append((start, min(end, sessions[-1])))
        while index < len(sessions) and sessions[index] <= end:
            index += 1
    return found
