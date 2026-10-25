"""The daily NSE margin job (story A14): each session's margin rows from its beginning-of-day SPAN file in Drive.

A structure's rows are written only from the day its independent broker check passed (`BrokerApprovals`, judge 77;
story STR1b); other rows are printed, not written. Days before the first approval are never pending (no row can ever be
written for them); with no approval at all, every day is refused by name. For every
session from a week before the due day up to it that has no NSE row yet, the job reads the day's `i1` file as first
archived (A9; A11 keeps later versions apart), checks it was written before 09:00 IST on that day (point in time: a
decision on d never sees a later file), computes the rows and appends them to `margins.csv`.

Fail closed: a missing or invalid file, a file written too late or a conflicting row writes nothing for that day; a
structure that cannot be computed gets no row. Every problem is named in one #fno-desk line and the run fails, so C2
keeps refusing what has no fresh margin. The next run retries the same days.
"""

from __future__ import annotations

import hashlib
import traceback
from collections.abc import Callable
from datetime import date, datetime, timedelta

from ..alerts.sender import AlertSender
from ..constants import MARGIN_SOURCE_NSE_SPAN
from ..fo_bhavcopy import BadFile
from .broker_approvals import NOT_PASSED, BrokerApprovals
from .calculator import MarginOutsideModel
from .margin_log import MarginLog, MarginLogConflict
from .rows import MarginRowBuilder
from .span_file import read_span_file

LOOKBACK_DAYS = 7  # a missed run is caught up within C2's 7-day margin age
MAX_GAP_DAYS = 15  # the longest NSE break between sessions is far shorter; beyond it the calendar lacks the year
ADDED = "nse margins: {day}: {rows} rows from {file}"
HELD = "nse margins: {day}: {rows} rows not written, no broker check approves {codes} by this day (printed for one):"
NOTHING_NEW = "nse margins: nothing new up to {day}"
ALERT = "Omenix F&O NSE margins: {problems}. C2 keeps refusing trades without a fresh margin; the next run retries"
DayFile = Callable[[date], tuple[str, bytes | None]]  # day -> (original file name, its first archived bytes or None)


class MarginDayProblem(RuntimeError):
    """A day writes no rows, for the named reason."""


def due_session(now: datetime, is_trading_day: Callable[[date], bool]) -> date:
    """The first session from today on: the job runs in the morning, when its `i1` file is out (NSE wrote 131 sampled
    files between 18:00 and 03:05 IST before their day; 2026's between 20:00 and 24:00). An evening run waits for the
    next morning rather than racing NSE's evening file."""
    start = now.date()
    for day in (start + timedelta(days=offset) for offset in range(MAX_GAP_DAYS)):
        if is_trading_day(day):
            return day
    raise MarginDayProblem(f"NSE's session calendar has no session within {MAX_GAP_DAYS} days of {start}")


class NseMarginJob:
    def __init__(self, day_file: DayFile, builder: MarginRowBuilder, log: MarginLog,
                 is_trading_day: Callable[[date], bool], check: BrokerApprovals, alerts: AlertSender,
                 now: Callable[[], datetime], print_line=print):  # fmt: skip
        self.day_file, self.builder, self.log, self.is_trading_day = day_file, builder, log, is_trading_day
        self.check, self.alerts, self.now, self.print_line = check, alerts, now, print_line

    def pending_days(self, due: date) -> list[date]:
        done, first = self.log.days_from(MARGIN_SOURCE_NSE_SPAN), self.check.first_day()
        days = (due - timedelta(days=offset) for offset in range(LOOKBACK_DAYS, -1, -1))
        return [d for d in days if self.is_trading_day(d) and d not in done and (first is None or d >= first)]

    def run(self) -> int:
        due, days, problems = None, [], []
        try:
            due = due_session(self.now(), self.is_trading_day)
            days = self.pending_days(due)
        except (MarginDayProblem, MarginLogConflict) as exc:
            problems.append(str(exc))
        except Exception as exc:  # noqa: BLE001 - e.g. a year missing from A7's calendar: one line, not a traceback
            problems.append(_unexpected(exc))
        for day in days:
            try:
                problems += self._add_day(day)
            except (MarginDayProblem, MarginLogConflict) as exc:
                problems.append(f"{day}: {exc}")
            except Exception as exc:  # noqa: BLE001 - named in the line, with the traceback in the log
                problems.append(f"{day}: {_unexpected(exc)}")
        if not days and not problems:
            self.print_line(NOTHING_NEW.format(day=due))
        if problems:
            self.print_line(self.alerts.send(ALERT.format(problems="; ".join(problems))))
            return 1
        return 0

    def _add_day(self, day: date) -> list[str]:
        try:
            filename, data = self.day_file(day)
        except Exception as exc:  # noqa: BLE001 - a refused Drive read is alerted, never only a traceback
            raise MarginDayProblem(f"the Drive read failed ({type(exc).__name__}: {exc})") from exc
        if data is None:
            raise MarginDayProblem(f"{filename} is not archived in Drive")
        try:
            span = read_span_file(data, filename)
        except BadFile as exc:
            raise MarginDayProblem(str(exc)) from exc
        if not span.written_in_time(day):
            deadline = span.deadline(day)
            raise MarginDayProblem(f"{filename} was written {span.created:%Y-%m-%d %H:%M}, not before {deadline:%H:%M}")
        try:
            found = self.builder.rows(span, hashlib.sha256(data).hexdigest(), day)
        except MarginOutsideModel as exc:
            raise MarginDayProblem(str(exc)) from exc
        if not self.check.any_by(day):
            for row in found.rows:
                self.print_line(",".join(row.as_csv().values()))
            raise MarginDayProblem(NOT_PASSED.format(rows=len(found.rows)))
        checked = [row for row in found.rows if self.check.approves(row.structure, day)]
        self._print_held(day, [row for row in found.rows if not self.check.approves(row.structure, day)])
        added = self.log.append(checked)
        self.print_line(ADDED.format(day=day, rows=added, file=filename))
        return [f"{day}: {reason}" for reason in found.skipped]

    def _print_held(self, day: date, rows: list) -> None:
        """Rows of structures no broker check approves by this day (stories STR1, STR1b): printed for that check, never
        written. Not an alert: C2 and C4 already refuse a structure without a fresh row."""
        if rows:
            codes = sorted({row.structure for row in rows})
            self.print_line(HELD.format(day=day, rows=len(rows), codes=", ".join(codes)))
            for row in rows:
                self.print_line(",".join(row.as_csv().values()))


def _unexpected(exc: Exception) -> str:
    traceback.print_exc()
    return f"stopped by an unexpected {type(exc).__name__}: {exc}"
