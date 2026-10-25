"""The 3 pm quote parts inside the daily run (story O1, A4c's passed routine steps 2-3b, judge 169): NIFTY (Groww) and
NSE start together at the run's start, the other indices right after NIFTY's commit (never before their own early
limit), each in its own window. They run as child processes beside the desk's steps, and the run's one thread
commits each part's own files when it ends, NIFTY first, through E3's committer (its guard, pull and push attempts),
never `research/data/quotes/` as a whole.

One git at a time: commits happen only in the run's one thread, between the desk's steps or while it waits
(`ServicingWaiter`), so a part's commit and a desk commit never interleave in the one checkout (criterion 4a)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from ..alerts.sender import AlertSender
from ..constants import STEP_FAILED, STEP_REFUSED
from ..desk.daily_ports import CommitFailed, Committer
from ..models import IST
from ..quotes.indices import INDEX_WINDOW_END, INDEX_WINDOW_START
from ..quotes.recorder import DATASET, NSE_DATASET, WINDOW_END, WINDOW_START, earliest_waiting_start
from ..quotes.weekly import WEEKLY_DATASET, WEEKLY_STEM
from .earlier_run import EarlierRun, PartMarkers
from .part_locks import PartLocks
from .processes import Process, Processes
from .steps import outcome

GROWW_QUOTES = ":(glob)research/data/quotes/groww/**/{name}_*"  # A4c's per-part paths, as CLAUDE.md gives them
# NIFTY's own dataset only: `groww/**/nifty_*` would also take a named window's files (G10: `quote-snapshots-v4`)
NIFTY_QUOTES = f":(glob)research/data/quotes/{DATASET}/**/nifty_*"
INDICES = ("banknifty", "finnifty", "midcpnifty")
# G4: the run's one committer remembers the commit, so the desk's next push takes it to origin
NOT_PUSHED = "F&O daily run {day}: quote part {name} committed, NOT pushed (the next push carries it): {reason}"
NOT_COMMITTED = (
    "F&O daily run {day}: quote part {name} NOT committed: {reason}. Hand fix (CLAUDE.md): git add {specs}, commit and "
    "push; never --no-verify"
)
PART_NOT_OK = (
    "F&O daily run {day}: 3 pm quote part {name} {status}: {reason}; the day's {name} record may be missing: check its "
    "sidecar and canonical marker"
)
STILL_RUNNING = "still running {minutes} minutes after the desk's exits: stopped, nothing more committed for it"
NEVER_STARTED = "never started: the part it waits for did not end in time"
STILL_HELD = (
    "still running after {minutes} minutes, held by an earlier run's recorder: a 3 pm recorder of an earlier run "
    "still holds {lock}: stop it, then rerun"
)
HUNG = "still running at {at:%H:%M}, after its window: stopped, nothing of it committed"
NOT_IN_THIS_RUN = "not in this run: an earlier run started it and ended, its window has closed and a marker is missing"
STARTED, RESTARTED, ADOPTED, EARLIER = "started", "restarted", "adopted", "earlier run"  # each part's `how` (F1)
FINISH_LIMIT = timedelta(minutes=20)
START_MARGIN = timedelta(minutes=3)  # inside A4's early limit by this much, for a slow start or a late clock


def earliest_start(window_start: time) -> time:
    """A4's recorders refuse a start more than `MAX_EARLY_WAIT_SECONDS` before their window ("too early", nothing
    recorded): the earliest moment a part of that window may start, from A4's own constants."""
    return (datetime.combine(date.min, earliest_waiting_start(window_start)) + START_MARGIN).time()


EARLIEST_START = earliest_start(WINDOW_START)  # NIFTY's and NSE's: 14:38 today
# The indices' own (14:44 today): a NIFTY part that ends early never starts them "too early" (DRY2 R1, 24 Oct)
INDEX_EARLIEST_START = earliest_start(INDEX_WINDOW_START)


@dataclass(frozen=True)
class QuotePart:
    name: str
    arguments: tuple[str, ...]  # the part's own `python -m fno` command, unchanged
    pathspecs: tuple[str, ...]  # its own files, and only its own
    starts_after: str | None = None  # starts once this part has ended and its commit was made or tried
    not_before: time | None = None  # never starts earlier than this (A4's early limit), even once `starts_after` ended
    canonicals: tuple[tuple[str, str], ...] = ()  # (dataset, stem) of each canonical marker it records (A4)
    window_end: time = WINDOW_END  # a rerun restarts it only before this (A4's window; the indices' own)
    live_key: str | None = None  # its `daily.live_from` key; None: always live (A4's parts)
    apart: bool = False  # its own dataset and window: commits as soon as it ends, never after NIFTY (G10's `v4`)


QUOTE_PARTS = (
    QuotePart("nifty", ("quotes", "record"), (NIFTY_QUOTES,), not_before=EARLIEST_START,
              canonicals=((DATASET, "nifty"),)),
    QuotePart("nse", ("quotes", "record", "--source", "nse"), ("research/data/quotes/nse/",),
              not_before=EARLIEST_START, canonicals=((NSE_DATASET, "nifty"),)),
    QuotePart("indices", ("quotes", "record-indices"),
              tuple(GROWW_QUOTES.format(name=n) for n in (*INDICES, WEEKLY_STEM)), "nifty", INDEX_EARLIEST_START,
              canonicals=(*((DATASET, name) for name in INDICES), (WEEKLY_DATASET, WEEKLY_STEM)),  # A4f's weeklies
              window_end=INDEX_WINDOW_END),
)  # fmt: skip
LEAD = QUOTE_PARTS[0].name  # NIFTY commits first: no other part commits before NIFTY's commit was made or tried


class QuoteParts:
    def __init__(
        self,
        parts: Sequence[QuotePart],
        processes: Processes,
        committer: Committer,
        changed: Callable[[Sequence[str]], list],
        alerts: AlertSender,
        clock: Callable[[], datetime],
        locks: PartLocks,
        markers: PartMarkers,
        live: Mapping[str, date | None] | None = None,
    ):
        """`live`: each `live_key`'s first live date (`daily.live_from`); a part whose key is not live on the day is
        not a part of that day (its steps, sharing the key, record `not_live`)."""
        self.parts, self.processes, self.committer, self.changed, self.alerts, self.clock = (
            parts,
            processes,
            committer,
            changed,
            alerts,
            clock,
        )
        self.locks, self.markers, self.live = locks, markers, live or {}
        self.every_part = tuple(parts)
        self.day: date | None = None
        self.running: dict[str, Process] = {}
        self.results: dict[str, dict] = {}
        self.how: dict[str, str] = {}  # each part's `how` (F1)
        self.closed = False  # past the finish limit: no part starts any more

    def start(self, day: date) -> list[str]:
        """Opens the day, once: every part that waits for no other starts now, or at its `not_before` if that is
        later (`start_due`); the names of those parts."""
        if self.day != day:
            self._open(day)
            self.start_due()
        return [part.name for part in self.parts if part.starts_after is None]

    def resume(self, day: date) -> None:
        """A rerun whose log holds `quotes` but not `quotes_done` (F1; judge 412 add. 2-3, judge 417). Each part is
        adopted while an earlier run's recorder still holds its lock (never a second recorder), taken from the earlier
        run when every canonical marker exists, restarted while its window is open, and otherwise failed with one
        alert. NIFTY still commits first and the indices still start after it, whatever each part's `how`."""
        self._open(day)
        for part in self.parts:
            if self.locks.held(day, part.name):
                self._earlier(part, ADOPTED)
            elif self.markers.recorded(day, part.canonicals):
                self._earlier(part, EARLIER)
            elif self.clock() < datetime.combine(day, part.window_end, IST):
                self.how[part.name] = RESTARTED
            else:
                self._failed(part.name, NOT_IN_THIS_RUN)
        self.start_due()

    def start_due(self) -> None:
        """Starts each part whose time has come and whose part to wait for (if any) has ended; never runs git, so any
        wait of the run may call it, a command's included. Before the day is opened (by `start` or `resume`; a rerun
        whose log holds the whole day opens neither) there is nothing to start."""
        if not self.started:
            return
        for part in self.parts:
            if not self.closed and self._unstarted(part) and self._waited_for(part) and self._due(part):
                self._start(part)

    @property
    def started(self) -> bool:
        return self.day is not None

    def busy(self) -> bool:
        return self.started and len(self.results) < len(self.parts)

    def recording(self) -> bool:
        """True while a part's recorder is running (story REH1: a rehearsal's waits run at real speed then)."""
        return bool(self.running)

    def next_start(self) -> datetime | None:
        """The earliest moment a part still to start may start (story REH1: a skipped wait never passes it)."""
        if not self.started or self.closed:
            return None
        due = [datetime.combine(self.day, part.not_before, IST) for part in self.parts
               if self._waited_for(part) and part.not_before is not None and self._unstarted(part)]  # fmt: skip
        return min(due, default=None)

    def service(self) -> None:
        """Starts the parts now due, commits every part that has ended (NIFTY's first), then starts the parts waiting
        for it whose time has come."""
        self.start_due()
        for name, process in list(self.running.items()):
            code = process.poll()
            if code is not None and (name == LEAD or LEAD in self.results or self._part(name).apart):
                self._finish(self._part(name), code, process.lines(), process.alerted(), process.errors())
        self.start_due()

    def finish(self, wait: Callable[[datetime], None], not_before: datetime | None = None) -> dict[str, dict]:
        """Waits for the parts still running (servicing them), at most `FINISH_LIMIT`; their results. Past the limit
        a part still running is stopped (its files are not committed: they may be half-written), the parts that ended
        are committed and a part never started stays so."""
        limit = max(self.clock() + FINISH_LIMIT, not_before or self.clock())  # a stop at 14:35 waits past the windows
        self.service()
        while self.busy() and self.clock() < limit:
            wait(min(limit, self.clock() + timedelta(seconds=5)))
            self.service()
        self.closed = True
        for name, process in list(self.running.items()):
            if process.poll() is None:
                process.stop()
                del self.running[name]
                self._failed(name, self._still_running(name))
        self.service()
        for part in self.parts:
            if part.name not in self.results:
                self._failed(part.name, NEVER_STARTED)
        return self.results

    def _open(self, day: date) -> None:
        """The day's parts: every part whose live key (if any) is live on `day` (`daily.live_from`)."""
        self.day = day
        self.parts = tuple(part for part in self.every_part if self._live(part, day))

    def _live(self, part: QuotePart, day: date) -> bool:
        live_from = self.live.get(part.live_key) if part.live_key else day
        return live_from is not None and live_from <= day

    def await_part(self, name: str, limit: datetime, wait: Callable[[datetime], None]) -> None:
        """Waits (servicing every part) until the part `name` has ended and its commit was made or tried, at most until
        `limit`; one still running then is stopped and failed, its files not committed (G10's release reads only an
        ended capture)."""
        if not self.waits_for(name):
            return
        self.service()
        while self.started and name not in self.results and self.clock() < limit:
            wait(min(limit, self.clock() + timedelta(seconds=5)))
            self.service()
        if name in self.running:
            adopted = self.how.get(name) == ADOPTED  # an earlier run's recorder: never stopped from here (F1)
            reason = self._still_running(name) if adopted else HUNG.format(at=limit)
            self.running.pop(name).stop()
            self._failed(name, reason)

    def waits_for(self, name: str) -> bool:
        """Whether the part `name` is a part of the day (live) that has not ended yet."""
        return self.started and name in {part.name for part in self.parts} and name not in self.results

    def _waited_for(self, part: QuotePart) -> bool:
        return part.starts_after is None or part.starts_after in self.results

    def _due(self, part: QuotePart) -> bool:
        return part.not_before is None or self.clock() >= datetime.combine(self.day, part.not_before, IST)

    def _unstarted(self, part: QuotePart) -> bool:
        return part.name not in self.running and part.name not in self.results

    def _start(self, part: QuotePart) -> None:
        """The child inherits the part's lock and holds it for its life; a lock still held means a recorder of another
        run is alive here, so it is adopted instead of starting a second one."""
        with self.locks.taken(self.day, part.name, self.clock()) as lock:
            if lock is None:
                return self._earlier(part, ADOPTED)
            self.running[part.name] = self.processes.start(part.arguments, hold=lock)
        self.how.setdefault(part.name, STARTED)

    def _earlier(self, part: QuotePart, how: str) -> None:
        day, name = self.day, part.name
        self.running[name] = EarlierRun(lambda: self.locks.held(day, name), self.markers, day, part.canonicals)
        self.how[name] = how

    def _still_running(self, name: str) -> str:
        minutes = int(FINISH_LIMIT.total_seconds() // 60)
        if self.how.get(name) == ADOPTED:
            return STILL_HELD.format(minutes=minutes, lock=self.locks.path(self.day, name))
        return STILL_RUNNING.format(minutes=minutes)

    def _logged(self, name: str, result: dict) -> dict:
        """How the part ran in this run and when it was started, by whichever run started it (the lock's record)."""
        return result | {"how": self.how.get(name, STARTED), "started_at": self.locks.started(self.day, name)}

    def _finish(self, part: QuotePart, code: int, lines: list[str], alerted: bool, errors: list[str]) -> None:
        del self.running[part.name]
        result = outcome(part.arguments, code, lines, errors=errors).result
        files = self.changed(part.pathspecs)
        try:
            message = f"3 pm quotes {self.day} {part.name}"
            result["commit"] = self.committer.commit(files, message) if files else self._earlier_commit(part)
        except CommitFailed as failed:
            result |= {"commit": None, "commit_error": str(failed)}
            self.alerts.send(self._commit_alert(part, failed))
        self.results[part.name] = self._logged(part.name, result)
        if result["status"] in (STEP_FAILED, STEP_REFUSED) and not alerted:
            self._alert(part.name, result)  # a part that failed without alerting (a Groww outage): O2's case

    def _commit_alert(self, part: QuotePart, failed: CommitFailed) -> str:
        if failed.unpushed:
            return NOT_PUSHED.format(day=self.day, name=part.name, reason=failed)
        specs = " ".join(f"'{spec}'" for spec in part.pathspecs)
        return NOT_COMMITTED.format(day=self.day, name=part.name, reason=failed, specs=specs)

    def _earlier_commit(self, part: QuotePart) -> str | None:
        """An earlier run's part with nothing left to commit: the commit holding its markers."""
        if self.how.get(part.name) not in (ADOPTED, EARLIER):
            return None
        return self.markers.recorded(self.day, part.canonicals)

    def _failed(self, name: str, reason: str) -> None:
        self.results[name] = self._logged(name, {"status": STEP_FAILED, "reason": reason, "commit": None})
        self._alert(name, self.results[name])

    def _alert(self, name: str, result: dict) -> None:
        """Every part that did not record is alerted once: by itself, or here (owner, 16 Oct: every failure alerts)."""
        self.alerts.send(PART_NOT_OK.format(day=self.day, name=name, status=result["status"], reason=result["reason"]))

    def _part(self, name: str) -> QuotePart:
        return next(part for part in self.parts if part.name == name)
