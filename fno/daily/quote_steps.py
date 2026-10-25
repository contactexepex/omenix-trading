"""The quote parts as the daily run's steps (story O1): `quotes` starts them and goes on; `quotes_done`, after the
desk's exits, waits for those still running and records each part's result line and commit. `ServicingWaiter` is
the desk's waiter that commits a part as soon as it ends, while the desk waits for its next time."""

from __future__ import annotations

import time as clock_time
from collections.abc import Callable
from datetime import date, datetime, time

from ..constants import STEP_FAILED, STEP_OK
from ..desk.daily_ports import DayStep, Waiter
from ..desk.daily_steps import StepOutcome
from ..models import IST
from .quote_parts import QuotePart, QuoteParts

POLL_SECONDS = 5.0


class ServicingWaiter(Waiter):
    def __init__(
        self, parts: QuoteParts, now: Callable[[], datetime], sleep: Callable[[float], None] = clock_time.sleep
    ):
        self.parts, self.now, self.sleep = parts, now, sleep

    def until(self, moment: datetime) -> None:
        self.parts.service()
        while (left := (moment - self.now()).total_seconds()) > 0:
            self.sleep(min(POLL_SECONDS, left))
            self.parts.service()


def start_time(part: QuotePart) -> str:
    if part.starts_after:
        return f"after {part.starts_after}"
    return f"from {part.not_before:%H:%M}" if part.not_before else "at the run's start"


class StartQuoteParts(DayStep):
    def __init__(self, parts: QuoteParts):
        self.parts = parts

    def run(self, day: date) -> StepOutcome:
        """The reason names when each part starts, "nifty, nse from 14:38; indices after nifty" (judge 178 add. 19)."""
        self.parts.start(day)
        starts: dict[str, list[str]] = {}
        for part in self.parts.parts:
            starts.setdefault(start_time(part), []).append(part.name)
        reason = "; ".join(f"{', '.join(names)} {when}" for when, names in starts.items())
        return StepOutcome({"parts": [p.name for p in self.parts.parts]}, {"status": STEP_OK, "reason": reason})


class FinishQuoteParts(DayStep):
    def __init__(self, parts: QuoteParts, waiter: Waiter):
        self.parts, self.waiter = parts, waiter

    def run(self, day: date) -> StepOutcome:
        """The parts are always open here: started by this run's `quotes`, or resumed by a rerun (F1)."""
        return StepOutcome({}, parts_result(self.parts.finish(self.waiter.until)))


def parts_result(results: dict[str, dict]) -> dict:
    """`quotes_done`'s result for the parts' own results: failed unless every part is ok and committed."""
    bad = [name for name, result in results.items() if result["status"] != STEP_OK or result.get("commit_error")]
    reason = f"not ok: {', '.join(bad)}" if bad else "every part ok"
    return {"status": STEP_FAILED if bad else STEP_OK, "reason": reason, "parts": results}


WAITING_FOR_PART = "waiting for the {name} quote part to end, at most until {by:%H:%M} IST (never a hang)"


class AfterPart(DayStep):
    """Runs its step once the quote part `name` has ended and its commit was made or tried, at most at `by` IST: a part
    still running then is stopped (G10's `v4_release` after the `v4` capture, by 14:45). The wait is announced once,
    as every wait of the run is (story O1-day-lock: a silent wait reads as a hang)."""

    def __init__(self, step: DayStep, parts: QuoteParts, name: str, by: time, waiter: Waiter,
                 announce: Callable[[str], None] = print):  # fmt: skip
        self.step, self.parts, self.name, self.by, self.waiter, self.announce = step, parts, name, by, waiter, announce

    def run(self, day: date) -> StepOutcome:
        by = datetime.combine(day, self.by, IST)
        if self.parts.waits_for(self.name):
            self.announce(WAITING_FOR_PART.format(name=self.name, by=by))
        self.parts.await_part(self.name, by, self.waiter.until)
        return self.step.run(day)
