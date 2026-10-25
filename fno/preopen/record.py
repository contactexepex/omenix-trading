"""`python -m fno preopen record` (story A22): on a trading day, reads the four parts in their windows, saves each
part's answer write-once to Drive as soon as it ends, writes the day row once, appends one O10 capture-error row per
problem, commits the receipts and the rows (by 09:12 IST) and posts one #fno-desk line naming every problem. Then,
after those commits, A22d's open check of earlier sessions, committed the same way, with its own line only when it
has problems. Lines name parts, statuses and exception kinds only, never a value."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from ..alerts.sender import AlertSender
from ..health.capture_errors import CaptureError, CaptureErrorLog
from ..intraday.clock import ClockReading
from ..research_data.calendar import CalendarError
from ..storage.data_store import DataStore
from ..storage.manifest_commit import ManifestRecorder
from ..storage.raw_store import RawFileConflict
from .answers import BASIS_FLAT
from .day_row import EARLY_FILES, day_file, day_row, early_file, early_row, raw_file
from .label_read import LabelRead
from .open_check import OpenCheck
from .problems import Problem
from .run import LATE, OK, PartResult, PreopenRun

JOB = "preopen"
NOT_TRADING = "not a trading day"
PART_LINE = "{part} {status} ({reads} read(s)){detail}"
DONE, WITH_PROBLEMS = "pre-open recorded", "pre-open recorded with problems: {problems}"
ALERT = "A22 pre-open capture {day}: {problems}"
CHECK_WITH_PROBLEMS = "open check with problems: {problems}"
CHECK_ALERT = "A22 open check {day}: {problems}"
NOT_COMMITTED = " NOT committed"
DAY_ROW_TAKEN = "day row already written by an earlier run; this run's row not kept"
EARLY_TAKEN = "file already written by an earlier run; this run's not kept"
SAVE_ERRORS = (OSError, RuntimeError, ValueError)  # Drive and its settings; RawFileConflict is a RuntimeError


class PreopenRecorder:
    def __init__(self, is_trading_day: Callable[[date], bool], run: Callable[[Callable], PreopenRun],
                 store: DataStore, errors: CaptureErrorLog, committers: Sequence[ManifestRecorder],
                 alerts: AlertSender, clock: Callable[[], ClockReading], early_commit: ManifestRecorder,
                 check: OpenCheck, out=print, label_read: Callable[[Callable], LabelRead] = LabelRead):  # fmt: skip
        """`run`: builds the window run around the callback that saves each finished part; `early_commit` pushes a
        part's own file (GIFT Nifty) as soon as the part ends; `check`: A22d's open check, run after the commits."""
        self.is_trading_day, self.build_run, self.store, self.errors = is_trading_day, run, store, errors
        self.committers, self.alerts, self.clock, self.out = committers, alerts, clock, out
        self.early_commit, self.check, self.label_read = early_commit, check, label_read

    def record(self, day: date) -> int:
        try:
            if not self.is_trading_day(day):
                self.out(NOT_TRADING)
                return 0
        except CalendarError as error:
            return self._finish(day, [Problem("calendar", "stopped", str(error))])
        labels = self.label_read(lambda: self.check.labels(day))  # beside the capture: it never delays a window
        reading = self.clock()
        problems = [Problem("clock", "warning", warning)] if (warning := reading.warning()) else []
        results = self.build_run(lambda result: problems.extend(self._finished(day, result))).run(day)
        for result in results:
            self.out(PART_LINE.format(part=result.part, status=result.status, reads=result.reads,
                                      detail=f": {result.detail}" if result.detail else ""))  # fmt: skip
        problems += [Problem(r.part, r.status, r.detail) for r in results if r.status != OK]
        flat_labels, label_problems = labels.taken()
        problems += (label_problems if _has_flat_value(results) else []) + self._save_day_row(
            day, reading.day_cell(), results, flat_labels)  # fmt: skip
        captured = self._finish(day, problems)
        labels.finish()
        summary, check_problems = self.check.run(day)
        checked = self._finish(day, check_problems, (summary, CHECK_WITH_PROBLEMS, CHECK_ALERT))
        return max(captured, checked)

    def _finished(self, day: date, result: PartResult) -> list[Problem]:
        return self._save_raw(day, result) + (self._save_early(day, result) if result.part in EARLY_FILES else [])

    def _save_early(self, day: date, result: PartResult) -> list[Problem]:
        """The part's own write-once file and an immediate push of the receipts (owner e70525ee4: 08:50 edition)."""
        try:
            self.store.put(early_file(result.part, day), early_row(day, result))
        except RawFileConflict:
            return [Problem(f"{result.part} file", "taken", EARLY_TAKEN)]
        except SAVE_ERRORS as error:
            return [Problem(f"{result.part} file", "not saved to Drive", type(error).__name__)]
        outcome = self.early_commit.commit(f"pre-open {result.part} {day}")
        self.out(outcome)
        return [Problem(f"{result.part} file", "commit failed", outcome)] if NOT_COMMITTED in outcome else []

    def _save_raw(self, day: date, result: PartResult) -> list[Problem]:
        if result.answer is None:
            return []
        try:
            self.store.put(raw_file(day, result), result.answer.raw)
        except SAVE_ERRORS as error:
            return [Problem(result.part, "raw not saved to Drive", type(error).__name__)]
        return []

    def _save_day_row(self, day: date, clock: str, results: list[PartResult], labels: dict) -> list[Problem]:
        try:
            self.store.put(day_file(day), day_row(day, clock, results, labels))
        except RawFileConflict:
            return [Problem("day row", "taken", DAY_ROW_TAKEN)]
        except SAVE_ERRORS as error:
            return [Problem("day row", "not saved to Drive", type(error).__name__)]
        return []

    def _finish(self, day: date, problems: list[Problem], lines=(DONE, WITH_PROBLEMS, ALERT)) -> int:
        """Appends the O10 rows, commits, prints the last line and sends the one alert when there is a problem."""
        done, with_problems, alert = lines
        for problem in problems:
            self.errors.append(CaptureError(day, JOB, problem.step, problem.kind, problem.message, ""))
        for committer in self.committers:
            outcome = committer.commit(f"pre-open {day}")
            self.out(outcome)
            if NOT_COMMITTED in outcome:
                problems.append(Problem("commit", "failed", outcome))
        if not problems:
            self.out(done)
            return 0
        named = "; ".join(problem.line() for problem in problems)
        self.out(with_problems.format(problems=named))
        self.out(self.alerts.send(alert.format(day=day, problems=named)))
        return 1


def _has_flat_value(results: list[PartResult]) -> bool:
    """A late label read matters only on a day with a flat 09:15 value to label."""
    return any(r.status in (OK, LATE) and r.answer.reading.values.get(f"{r.part}_preopen_basis") == BASIS_FLAT
               for r in results)  # fmt: skip
