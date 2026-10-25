"""Book 1, pure rules (story E5, design 12.1 and 12.9): each session day it decides by code alone. D2's evaluation of
its approved (`paper`) playbook versions, with C2 on Book 1's own account, written as D3's decision record (whose
`chosen_action` is the rule's action) and committed before E3's deadline. It has no AI authority: nothing on its path
calls or imports a model.

With no `paper` version on the day it also commits "no approved strategy": a result, not an error. D2 still runs, so
registered research candidates are forward-tested in shadow and the day's record exists for replay. C4's failure log,
which the run appends to, is committed with the run (judge 84: an uncommitted row would block every account write).

One decision a day (story E5b, decisions 57 and 59 a): a run of the day found on origin, in `HEAD` or on disk is never
decided again, whatever the inputs; changed inputs are alerted, never acted on. The commit goes through E2b's
`PendingCommitter` with Book 1's own marker, so a failed commit's rerun commits the recorded files, never a new run."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..alerts.sender import AlertSender
from ..books.paths import book_folder
from ..constants import BOOK1_RULES, NO_APPROVED_STRATEGY, VALIDITY_FAILURES_FILE
from ..desk.pending_commit import PendingCommitter
from ..playbook.allocation import StrategyTradeCounts
from ..playbook.decision_inputs import PlaybookSnapshot
from ..playbook.decision_run import DecisionRun
from ..playbook.decision_store import INPUTS_FILE, DecisionStore
from ..playbook.evaluate import LiveFeatureValues
from ..playbook.schema import Strategy
from ..playbook.shadow import ShadowBooks
from ..research_data.calendar import SessionCalendar
from ..risk.inputs import Market, RiskBook
from .decided_runs import ON_DISK, DecidedRuns, FoundRun, changed_fields

NO_APPROVED_FILE = "no_approved_strategy.json"
PENDING_MARKER = ".pending_book1.json"  # Book 1's own, never the daily run's (story E5b)
DECIDED = "Book 1 {day}: decided ({run}), committed {commit}"
RECOVERED = "Book 1 {day}: decided ({runs}), committed on this rerun as recorded ({commit})"
ALREADY = "Book 1 {day}: already decided ({runs}); one decision a day, never decided again"
NOT_SESSION = "Book 1 {day}: not a session day, nothing decided"
CHANGED = "F&O Book 1 {day}: inputs changed after decision {run} ({file}: {fields}); not decided again"
DISK_ONLY = ("F&O Book 1 {day}: run {run} is on disk only (not committed, not recorded for recovery); nothing decided."
             " Fix: inspect it, then `fno desk book1 --day {day} --commit-run {run}` (commits it as recorded), or "
             "remove it before the deadline")  # fmt: skip
NOT_DISK_ONLY = "Book 1 {day}: {run} is not a run on disk only ({place}): nothing committed"
EDITED = "Book 1 {day}: {run} was edited after it was written ({files}): nothing committed"
COMMITTED_RUN = "Book 1 {day}: {run} committed as recorded ({commit})"


ShadowOpener = Callable[[Sequence[Strategy], date], list[str]]  # opens each research version's shadow account once


class CommitRunRefused(ValueError):
    """`--commit-run` commits only an unedited run that is on disk only; the message names why not."""


@dataclass(frozen=True)
class Book1Day:
    """Everything D2 reads for Book 1 on a day, and the run's context (hashes and links, D3's RUN_CONTEXT)."""

    market: Market
    features: LiveFeatureValues
    book: RiskBook
    counts: StrategyTradeCounts
    shadow: ShadowBooks
    context: Mapping[str, object]


class Book1Inputs(ABC):
    @abstractmethod
    def day(self, day: date) -> Book1Day:
        """Book 1's inputs on the day, from the two packs, the canonical snapshot and its own account."""


class Book1:
    def __init__(self, root: Path, calendar: SessionCalendar, playbook: Callable[[], PlaybookSnapshot],
                 inputs: Book1Inputs, run: DecisionRun, committer: PendingCommitter, decided: DecidedRuns,
                 alerts: AlertSender, open_shadows: ShadowOpener = lambda strategies, day: []):  # fmt: skip
        self.root, self.calendar, self.playbook, self.inputs, self.run = Path(root), calendar, playbook, inputs, run
        self.committer, self.decided, self.alerts, self.open_shadows = committer, decided, alerts, open_shadows
        self.store = DecisionStore(self.root, BOOK1_RULES)

    def decide(self, day: date) -> str:
        """One decision a day (decision 57): a pending commit is recovered first, and a run of the day found anywhere
        (origin, `HEAD`, disk) means nothing is decided again, whatever the inputs."""
        if not self.calendar.is_session(day):
            return NOT_SESSION.format(day=day)
        recovered = self.committer.recover()
        found = self.decided.find(day)
        if found:
            return self._already(day, found, recovered)
        snapshot = self.playbook()
        if not snapshot.playbook().approved_on(day):
            self._no_approved(day, snapshot)
        self.open_shadows(snapshot.playbook().shadow_on(day), day)  # before D2 reads them (story R3)
        inputs = self.inputs.day(day)
        run = self.run.decide(day, snapshot, inputs.market, inputs.features, inputs.book, inputs.counts,
                              inputs.shadow, inputs.context)  # fmt: skip
        return DECIDED.format(day=day, run=run.name, commit=self._commit(day, run))

    def commit_run(self, day: date, run_id: str) -> str:
        """The hand fix for a run on disk only: commits it exactly as written, through the same committer and checks;
        never runs D2 and never sets a commit date."""
        place = next((f.place for f in self.decided.find(day) if f.run_id == run_id), "not found")
        if place != ON_DISK:
            raise CommitRunRefused(NOT_DISK_ONLY.format(day=day, run=run_id, place=place))
        run = self.store.day_folder(day) / run_id
        edited = DecisionStore.edited(run)
        if edited:
            raise CommitRunRefused(EDITED.format(day=day, run=run_id, files=", ".join(edited)))
        return COMMITTED_RUN.format(day=day, run=run_id, commit=self._commit(day, run))

    def _already(self, day: date, found: list[FoundRun], recovered: str) -> str:
        snapshot, inputs = self.playbook(), self.inputs.day(day)
        fresh = self.run.inputs(day, snapshot, inputs.market, inputs.features, inputs.book, inputs.counts,
                                inputs.shadow)  # fmt: skip
        for run in found:  # one run a day in practice; each is compared, none is ranked here (D3b orders runs)
            if fields := changed_fields(run.inputs, fresh):
                self.alerts.send(CHANGED.format(day=day, run=run.run_id, file=INPUTS_FILE, fields=", ".join(fields)))
        on_disk = [f.run_id for f in found if f.place == ON_DISK]
        if on_disk:
            text = "\n".join(DISK_ONLY.format(day=day, run=run) for run in on_disk)
            self.alerts.send(text)
            return text
        if recovered:
            return RECOVERED.format(day=day, runs=", ".join(f.run_id for f in found), commit=recovered)
        return ALREADY.format(day=day, runs=", ".join(f"{f.run_id} {f.place}" for f in found))

    def _commit(self, day: date, run: Path) -> str:
        """The run's files one by one (the pending marker records each), the day's "no approved strategy" file and
        C4's failure log, which the run appends to (judge 84: an uncommitted row would block every account write)."""
        others = (
            self.store.day_folder(day) / NO_APPROVED_FILE,
            book_folder(self.root, BOOK1_RULES) / VALIDITY_FAILURES_FILE,
        )
        paths = sorted(p for p in run.iterdir() if p.is_file()) + [p for p in others if p.is_file()]
        return self.committer.commit(paths, f"Book 1 decision {day} ({run.name})")

    def _no_approved(self, day: date, snapshot: PlaybookSnapshot) -> None:
        path = self.store.day_folder(day) / NO_APPROVED_FILE
        body = {"kind": NO_APPROVED_STRATEGY, "book": BOOK1_RULES, "day": day.isoformat(),
                "registry_commit": snapshot.commit}  # fmt: skip
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(body, sort_keys=True, indent=1) + "\n", encoding="utf-8")
