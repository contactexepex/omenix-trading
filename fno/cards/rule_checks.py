"""The devil's advocate's rule checks on the card (story T2): they check nothing again. C4 refuses a trade at the
book's decision and writes `journal/<book>/validity_failures.csv`; C3 checks the data at the desk's execution
snapshot (the run log's `snapshot` step). T2 reads those committed records and makes the card say what they say. A
record is final only once the desk has recorded its step; before that it is "not yet decided", with the time the
desk's own `Timetable` gives for it, never "no breach". The registry stays T1's `RegistryStatus`."""

from __future__ import annotations

import csv
import io
import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, time

from ..constants import (
    BOOKS,
    CARD_DATA_CHECK_FAILED,
    CARD_HARD_RULE_BREACH,
    JOURNAL_FOLDER,
    RUN_LOG_DECISIONS_STEP,
    VALIDITY_FAILURES_FILE,
)
from ..desk.run_log import RUNS_FOLDER, book_results, problem_steps
from ..desk.timetable import Timetable
from .committed import CommittedRecords
from .sections import UsedRecord

SNAPSHOT_STEP = "snapshot"  # the desk's execution capture, where C3's checks run (fno/desk/daily_run.py)
NOT_RUN = "not yet decided: the desk has not run today"
PENDING = "not yet decided (final at {at:%H:%M} IST)"
UNREADABLE = "{path}: not readable ({why})"
MALFORMED = "steps are not name -> {result: {...}}"
STEP_PROBLEM = "decisions step {status}: {reason}"  # O1's R2 result, the orchestrator's wording (T1d)
STEP_STATUS = "decisions step {status}"  # a step-level result that logged no reason


@dataclass(frozen=True)
class RuleOutcome:
    name: str
    final: bool
    line: str
    code: str = ""  # a card reason code when a rule refused or a record is unreadable, else ""
    used: tuple[UsedRecord, ...] = ()


def run_log_path(day: date) -> str:
    return f"{JOURNAL_FOLDER}/{RUNS_FOLDER}/{day.isoformat()}.json"


def failures_path(book: str) -> str:
    return f"{JOURNAL_FOLDER}/{book}/{VALIDITY_FAILURES_FILE}"


class RunLogReader:
    """The day's committed run log steps; `None` when the desk has not run, `UnreadableRecord` when it is broken."""

    def __init__(self, records: CommittedRecords):
        self.records = records

    def steps(self, day: date) -> tuple[dict | None, tuple[UsedRecord, ...]]:
        path = run_log_path(day)
        data = self.records.read(path)
        if data is None:
            return None, ()
        try:
            steps = json.loads(data)["steps"]
        except (ValueError, KeyError, TypeError) as bad:
            raise UnreadableRecord(UNREADABLE.format(path=path, why=type(bad).__name__)) from None
        if not _well_formed(steps):  # checked once here, so no reader (nor O1's `problem_steps`) meets an odd shape
            raise UnreadableRecord(UNREADABLE.format(path=path, why=MALFORMED))
        return steps, (UsedRecord.of(path, data),)


def _well_formed(steps) -> bool:
    return isinstance(steps, dict) and all(isinstance(s, dict) and isinstance(s.get("result"), dict)
                                           for s in steps.values())  # fmt: skip


class UnreadableRecord(RuntimeError):
    """A rule's committed record exists but cannot be read: the card says `data_check_failed`, never "no breach"."""


class RuleSource(ABC):
    name: str

    @abstractmethod
    def outcome(self, day: date) -> RuleOutcome:
        """The rule's committed outcome for the day; raises `UnreadableRecord` when its record cannot be read."""


class DecisionOutcome(RuleSource):
    """Final once the run log has its `decisions` step (after `decision_deadline`): which books were on time, and the
    C4 refusals dated that day."""

    name = "decisions"

    def __init__(self, records: CommittedRecords, runs: RunLogReader, timetable: Timetable,
                 books: Sequence[str] = BOOKS):  # fmt: skip
        self.records, self.runs, self.at, self.books = records, runs, timetable.decision_deadline, tuple(books)

    def outcome(self, day: date) -> RuleOutcome:
        steps, used = self.runs.steps(day)
        if steps is None or RUN_LOG_DECISIONS_STEP not in steps:
            return RuleOutcome(self.name, False, _pending(steps, self.at), used=used)
        step = steps[RUN_LOG_DECISIONS_STEP]
        failed = bool(problem_steps({RUN_LOG_DECISIONS_STEP: step}))  # O1's one rule: failed or refused (T1d)
        refused, files = self._refusals(day)  # C4's refusals are read on every path, a failed step's too
        parts = [_decided(step["result"])]
        parts.append("C4 refused: " + "; ".join(f"{b} ({', '.join(c)})" for b, c in refused.items()) if refused
                     else "no C4 refusal")  # fmt: skip
        code = CARD_DATA_CHECK_FAILED if failed else CARD_HARD_RULE_BREACH if refused else ""
        return RuleOutcome(self.name, True, ", ".join(parts), code, used + files)

    def _refusals(self, day: date) -> tuple[dict[str, list[str]], tuple[UsedRecord, ...]]:
        refused, used = {}, []
        for book in self.books:
            path = failures_path(book)
            data = self.records.read(path)
            if data is None:
                continue  # no file: C4 never refused a trade of this book
            used.append(UsedRecord.of(path, data))
            try:
                rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
                checks = sorted({r["check"] for r in rows if r["day"] == day.isoformat()})
            except (KeyError, UnicodeDecodeError, csv.Error) as bad:
                raise UnreadableRecord(UNREADABLE.format(path=path, why=type(bad).__name__)) from None
            if checks:
                refused[book] = checks
        return refused, tuple(used)


class ExecutionOutcome(RuleSource):
    """Final once the run log has its `snapshot` step (after `execution_snapshot`): C3's verdict on the execution
    capture. A card built before then also shows the last session's verdict, which is final."""

    name = "execution"

    def __init__(self, runs: RunLogReader, timetable: Timetable, previous: Callable[[date], date | None]):
        self.runs, self.at, self.previous = runs, timetable.execution_snapshot, previous

    def outcome(self, day: date) -> RuleOutcome:
        steps, used = self.runs.steps(day)
        if steps is None or SNAPSHOT_STEP not in steps:
            return RuleOutcome(self.name, False, f"{_pending(steps, self.at)}; {self._last(day)}", used=used)
        line, code = _verdict(steps[SNAPSHOT_STEP]["result"])
        return RuleOutcome(self.name, True, line, code, used)

    def _last(self, day: date) -> str:
        previous = self.previous(day)
        if previous is None:
            return "last session: unknown (calendar)"
        steps, _ = self.runs.steps(previous)
        if steps is None or SNAPSHOT_STEP not in steps:
            return f"last session ({previous}): no execution record"
        return f"last session ({previous}): {_verdict(steps[SNAPSHOT_STEP]['result'])[0]}"


def _decided(result: dict) -> str:
    """A step-level result (O1's R2 and later: a top-level `status`, which no book id is) is shown as it is, never
    read as books (T1d); otherwise which books were late."""
    if "status" in result:
        reason = result.get("reason")
        return (
            STEP_PROBLEM.format(status=result["status"], reason=reason)
            if reason
            else STEP_STATUS.format(status=result["status"])
        )
    late = [b for b, r in book_results(result).items() if "run_id" not in r]
    return f"late or not committed: {', '.join(late)}" if late else "every book on time"


def _verdict(result: dict) -> tuple[str, str]:
    if result.get("valid"):
        return "valid execution snapshot", ""
    return f"no valid execution snapshot ({result.get('reason', 'no reason recorded')})", CARD_DATA_CHECK_FAILED


def _pending(steps: dict | None, at: time) -> str:
    return NOT_RUN if steps is None else PENDING.format(at=at)
