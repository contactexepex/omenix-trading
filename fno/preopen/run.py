"""Waits for each part's window and reads it until complete (story A22, criterion 4): first read at the window's
opening, then every 30 s, the last at its `last_read_margin` before its close (09:10:59 for 09:11:00; the index parts'
09:10:45, A22e). A part complete inside its window is `ok`; complete only from its close on (a run started late reads
once) is `late`; never complete is `incomplete`, or `failed` when no read gave a usable answer. Parts' windows may
overlap; reads happen in time order. Each part is handed to `finished` as soon as it ends, so its answer is saved
before later windows."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ..models import IST
from .answers import BadAnswer
from .parts import Answer, PartFailed, PreopenPart

RETRY_EVERY = timedelta(seconds=30)
OK, LATE, INCOMPLETE, FAILED = "ok", "late", "incomplete", "failed"


@dataclass
class PartResult:
    part: str
    status: str
    reads: int
    answer: Answer | None  # the last usable answer (complete or not)
    detail: str  # why it is not ok


@dataclass
class _Plan:
    part: PreopenPart
    opens: datetime
    closes: datetime
    next_at: datetime
    reads: int = 0
    answer: Answer | None = None
    problem: str = ""


class PreopenRun:
    def __init__(self, parts: Sequence[PreopenPart], now: Callable[[], datetime], sleep: Callable[[float], None],
                 finished: Callable[[PartResult], None] = lambda result: None):  # fmt: skip
        self.parts, self.now, self.sleep, self.finished = parts, now, sleep, finished

    def run(self, day: date) -> list[PartResult]:
        plans = [self._plan(part, day) for part in self.parts]
        results: dict[str, PartResult] = {}
        while len(results) < len(plans):
            waiting = [plan for plan in plans if plan.part.name not in results]
            due = min(waiting, key=lambda plan: plan.next_at)
            now = self.now()
            if due.next_at > now:
                self.sleep((due.next_at - now).total_seconds())
                continue
            result = self._read(due)
            if result is not None:
                results[result.part] = result
                self.finished(result)
        return [results[part.name] for part in self.parts]

    @staticmethod
    def _plan(part: PreopenPart, day: date) -> _Plan:
        opens, closes = (datetime.combine(day, at, IST) for at in part.window)
        return _Plan(part, opens, closes, opens)

    def _read(self, plan: _Plan) -> PartResult | None:
        """One read; the part's result when it is over, else None with its next read planned."""
        plan.reads += 1
        try:
            plan.answer = plan.part.answer(plan.opens.date())
            plan.problem = plan.answer.reading.detail
        except (PartFailed, BadAnswer) as problem:
            plan.problem = str(problem)
        now, last_read = self.now(), plan.closes - plan.part.last_read_margin
        if plan.answer is not None and plan.answer.reading.complete:
            if plan.answer.seen_at < plan.closes:
                return self._result(plan, OK, "")
            return self._result(plan, LATE, f"seen {plan.answer.seen_at.astimezone(IST):%H:%M:%S}")
        if now >= last_read:
            return self._result(plan, INCOMPLETE if plan.answer is not None else FAILED, plan.problem)
        plan.next_at = min(now + RETRY_EVERY, last_read)
        return None

    @staticmethod
    def _result(plan: _Plan, status: str, detail: str) -> PartResult:
        return PartResult(plan.part.name, status, plan.reads, plan.answer, detail)
