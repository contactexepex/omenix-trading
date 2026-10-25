"""Firing the post-mortem's one AI routine (story LR1): step 1 writes the summary, step 2 the objections. It is fired
through the AI books' `RoutineTrigger` (only a one-line pointer: the Saturday and the committed lines' SHA-256), once
per week, never retried; not at all when BG1's month signal says AI roles stop (design 7.6). The fire log
(`<Saturday>_fired.json`) keeps the run's session link for F8's audit, or why it was not fired."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..budget.signal import signal_path
from ..pipeline.trigger import FireFailed, RoutineTrigger
from .report import PostMortemRecords, sha256_of

FIRED_SUFFIX = "_fired.json"
JOB = "weekly_postmortem"
LINE = "Omenix F&O weekly post-mortem {saturday}: {result}"
BUDGET_STOP = "AI roles stopped by the budget (BG1 signal: stop)"
NO_LINES = "no committed lines for the week; run `postmortem weekly --post` first"


@dataclass(frozen=True)
class WriterPointer:
    week_ending: date
    lines_sha256: str

    def to_text(self) -> str:
        return json.dumps({"job": JOB, "lines_sha256": self.lines_sha256, "week_ending": self.week_ending.isoformat()},
                          sort_keys=True)  # fmt: skip


class BudgetSignal(ABC):
    @abstractmethod
    def ai_roles_stopped(self, day: date) -> bool: ...


class SignalFile(BudgetSignal):
    """BG1's `accounting/budget/<YYYY-MM>_signal.json`; no file for the month means no stop."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def ai_roles_stopped(self, day: date) -> bool:
        path = self.root / signal_path(f"{day:%Y-%m}")
        return path.is_file() and json.loads(path.read_text(encoding="utf-8")).get("stop_ai_roles") is True


class PostMortemRoutine:
    def __init__(self, trigger: RoutineTrigger, records: PostMortemRecords, budget: BudgetSignal,
                 clock: Callable[[], datetime]):  # fmt: skip
        self.trigger, self.records, self.budget, self.clock = trigger, records, budget, clock

    def fire(self, saturday: date) -> str:
        lines = self.records.path(saturday)
        if not lines.is_file():
            return LINE.format(saturday=saturday, result=NO_LINES)
        if self.records.read_json(saturday, FIRED_SUFFIX) is not None:
            return LINE.format(saturday=saturday, result="already fired (once per week)")
        log = self._fire(WriterPointer(saturday, sha256_of(lines)))
        self.records.write_json_once(saturday, FIRED_SUFFIX, log)
        return LINE.format(saturday=saturday, result="routine fired" if log["fired"] else f"not fired: {log['reason']}")

    def _fire(self, pointer: WriterPointer) -> dict:
        log = {"pointer": pointer.to_text(), "at": self.clock().isoformat()}
        if self.budget.ai_roles_stopped(pointer.week_ending):
            return {**log, "fired": False, "reason": BUDGET_STOP}
        try:
            link = self.trigger.fire(pointer)
        except FireFailed as failure:
            return {**log, "fired": False, "reason": str(failure)}
        return {**log, "fired": True, "session_link": link}
