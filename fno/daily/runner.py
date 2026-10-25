"""The day as one command (story O1): the daily run, then its one result line. After E3's commit-failure stop
(decision 44) the card does not run and nothing more of the desk is committed; the quote parts still running are
waited for and commit their own files (they are the recorder's data, not the desk's records)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..desk.daily_ports import Waiter
from ..desk.daily_run import DailyRun, RunStopped
from ..desk.run_log import RunLog, problem_steps, retried_steps
from .quote_parts import QuoteParts

DAY_DONE = "day done"
WITH_PROBLEMS = "day done with problems: {steps}"
NO_CARD = "; no card today"
# Owner, 24 Oct ("2 - yes"): the routine reruns once at once when the line says so (CLAUDE.md "Daily desk routine");
# a Slack alert that was sent is not printed, so the last line is where the routine reads it
RETRIES = "; a rerun today retries it: {steps}"
QUOTES_STEP, QUOTES_DONE_STEP = "quotes", "quotes_done"


class DayRunner:
    def __init__(
        self,
        daily_run: DailyRun,
        parts: QuoteParts,
        waiter: Waiter,
        before: Callable[[], None] = lambda: None,
        after: Callable[[date], None] = lambda day: None,
    ):
        """`after`: the run's last act once it ends without a stop (O1-status-only: the full log's Drive copy). A
        stopped run's committer is what failed, so its copy waits: the rerun that recovers the day copies the whole
        day's full log, the stopped attempt's steps included; a crash or a killed container never gets there."""
        self.daily_run, self.parts, self.waiter, self.before, self.after = daily_run, parts, waiter, before, after

    def run(self, day: date) -> tuple[int, str]:
        ended = self._run(day)
        if not ended[1].endswith(NO_CARD):
            self.after(day)
        return ended

    def _run(self, day: date) -> tuple[int, str]:
        """The exit code and the one line the command ends on. The quote parts start first, before the whole-history
        fetch (`before`) and the run's Drive download, so neither a hung fetch nor a Drive outage can delay or lose the
        day's quotes, NSE included (judge D and the orchestrator, 16 Oct). A rerun whose log already holds `quotes`
        but not `quotes_done` resumes them (gap F1): an earlier run's part is adopted or taken as recorded, one whose
        window is still open is restarted."""
        log = RunLog.open(self.daily_run.steps.root, day)
        if not log.done(QUOTES_STEP):
            self.parts.start(day)  # first: neither the history fetch nor the Drive download can delay the 3 pm parts
        elif not log.done(QUOTES_DONE_STEP):
            self.parts.resume(day)
        self.before()
        try:
            log = self.daily_run.run(day)
        except RunStopped as stopped:
            self._finish_parts(day)
            return 1, f"{stopped}{NO_CARD}"
        self._finish_parts(day)  # a closed day records only `skipped`: its parts (each "not a trading day") end here
        problems = [name for name, _ in problem_steps(log.steps)]
        if not problems:
            return 0, DAY_DONE
        return 1, WITH_PROBLEMS.format(steps=", ".join(problems)) + self._retries(day, log)

    def _retries(self, day: date, log: RunLog) -> str:
        """The steps a rerun now would run again: only on the run's own day (`DailyRun` retries nothing later)."""
        retried = retried_steps(log.steps) if self.daily_run.on_its_day(day) else []
        return RETRIES.format(steps=", ".join(retried)) if retried else ""

    def _finish_parts(self, day: date) -> None:
        """Waits at least until the desk's `fills_by` (after every part's own window, read from the timetable), so a
        run stopped early still lets each part end and commit its files."""
        if self.parts.busy():
            times = self.daily_run.steps.timetable
            self.parts.finish(self.waiter.until, times.at(day, times.fills_by))
