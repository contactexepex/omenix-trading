"""`python -m fno global-cues preopen` (story A17e part B), started by A22's pre-open routine beside its own command
(both run from about 08:36 IST in one checkout). It waits for its own window on its own clock: no read starts before
`WINDOW_OPENS` or after `WINDOW_CLOSES` (an index not reached by then is a failure), so its commit (its snapshot logs
and, after a failure, O10's row; pulled with `--no-rebase`, the push retried) is done before A22's push at about 09:11.

One line per Asian index. Any problem, from building the reader (Drive settings missing, an expired Drive sign-in) to
one index's read, an index with no session data or a closures calendar that does not cover the year (story A17f),
posts one #fno-desk line naming each problem and its reason, and appends one row per O10 kind to O10's capture-error
log (a routine, not a workflow: O10's `record-error` row; `incomplete` for data that did not come, `failure` for the
rest), then exits 1; so does a morning where no open market gave a live level (every one `stale`: Yahoo's feed
paused). Lines and the alert name indexes, statuses, reasons and error classes only, never a level (private, owner
rule 50a79a43)."""

from __future__ import annotations

import time as clock_time
from collections.abc import Callable
from datetime import datetime, time

import requests

from ..research_data.calendar import CalendarError
from .preopen import LIVE, STALE
from .preopen_outcome import FAILURE, Problem

# every failure one index's read can meet: the network (a block included), the answer, Drive, the private table
FAILURES = (
    requests.RequestException,
    ValueError,
    KeyError,
    TypeError,
    IndexError,
    ArithmeticError,
    RuntimeError,
    OSError,
)
JOB, STEP = "global-cues-preopen", "preopen"
ALERT = "Omenix F&O pre-open Asian levels: {what}"
ALL_STALE = "no live level: every open market stale"
WINDOW_OPENS, WINDOW_CLOSES = time(8, 50), time(9, 5)  # IST: after A22's GIFT Nifty read, before its pre-open read
CLOSED_WINDOW = "{index}: FAILED, not read: the window closed at 09:05 IST"
CLOSED_WINDOW_PROBLEM = "{index}: failed (not read: the window closed at 09:05 IST)"
NOT_COMMITTED_MARK = "NOT committed"
NOT_A_TRADING_DAY = "preopen: not a trading day (NSE's calendar): nothing read"


def cmd_preopen(out=print, now: Callable[[], datetime] | None = None, sleep=clock_time.sleep, is_session=None) -> int:
    """`is_session(day)`: NSE's calendar (A7) decides the day, as for every desk capture; a closed day reads nothing."""
    from ..models import now_ist
    from .wiring import build_preopen, build_preopen_committers, nse_session_day

    now, is_session = now or now_ist, is_session or nse_session_day
    try:
        trading = is_session(now().date())
    except (
        CalendarError
    ) as exc:  # a year the calendar does not hold yet: the run's one alert and row (judge 439 add. 1)
        out(f"preopen: STOPPED, NSE's calendar cannot answer ({type(exc).__name__})")
        _record([Problem("NSE calendar cannot answer for today")])
        out(_alert("NSE calendar cannot answer for today"))
        return 1
    if not trading:
        out(NOT_A_TRADING_DAY)
        return 0
    _wait_for_window(now, sleep)
    problems = []
    try:
        reader, sources = build_preopen()
    except FAILURES as exc:
        out(f"preopen: STOPPED before any read ({type(exc).__name__})")
        problems.append(Problem(f"stopped before any read ({type(exc).__name__})"))
    else:
        problems += _read_all(out, reader, sources, now)
    if problems:  # the rows first, so the commit below carries them
        _record(problems)
    if not _committed(out, build_preopen_committers):
        problems.append(Problem("receipts not committed"))
    if not problems:
        return 0
    out(_alert("; ".join(p.text for p in problems)))  # one line for everything that went wrong
    return 1


def _wait_for_window(now: Callable[[], datetime], sleep) -> None:
    current = now()
    opens = datetime.combine(current.date(), WINDOW_OPENS, tzinfo=current.tzinfo)
    if (wait := (opens - current).total_seconds()) > 0:
        sleep(wait)


def _read_all(out, reader, sources, now: Callable[[], datetime]) -> list[Problem]:
    """Each index's lines; the problems found (each index's own, or no live level on a morning with open markets)."""
    problems, statuses = [], []
    for index, source in sources:
        if now().time() >= WINDOW_CLOSES:
            problems.append(Problem(CLOSED_WINDOW_PROBLEM.format(index=index)))
            out(CLOSED_WINDOW.format(index=index))
            continue
        try:
            found = reader.read(source, index)
        except FAILURES as exc:
            problems.append(Problem(f"{index}: failed ({type(exc).__name__})"))
            out(f"{index}: FAILED ({type(exc).__name__}): {exc}")
            continue
        for line in found.lines:
            out(line)
        problems += found.problems
        statuses.append(found.status)
    if STALE in statuses and LIVE not in statuses:
        problems.append(Problem(ALL_STALE))
    return problems


def _committed(out, committers: Callable[[], list]) -> bool:
    """Its own files only (owned paths), whatever the reads gave; False when they could not be pushed."""
    try:
        lines = [committer.commit("pre-open Asian levels") for committer in committers()]
    except FAILURES as exc:
        lines = [f"pre-open receipts {NOT_COMMITTED_MARK}: {type(exc).__name__}"]
    for line in lines:
        out(line)
    return not any(NOT_COMMITTED_MARK in line for line in lines)


def _record(problems: list[Problem]) -> None:
    """One O10 row per kind (a routine's problems: O10's `record-error` row), failures first."""
    from ..health.capture_errors import CaptureError, one_line
    from ..health.wiring import build_capture_error_log
    from ..models import now_ist

    log, day = build_capture_error_log(), now_ist().date()
    for kind in sorted({p.kind for p in problems}, key=lambda kind: kind != FAILURE):
        what = "; ".join(p.text for p in problems if p.kind == kind)
        log.append(CaptureError(day, JOB, STEP, kind, one_line(what), ""))


def _alert(what: str) -> str:
    from ..composition import build_alert_sender

    return build_alert_sender().send(ALERT.format(what=what))
