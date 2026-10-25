"""Every report in a rehearsal (story REH1c; the orchestrator's ruling for the owner, 24 Oct: "all type of data and
reports ... send to slack for review"): a step that is not live on the replayed day in real runs runs in the
rehearsal, and each of its posts says so in one more line. Chosen in the daily run's composition root; real runs and
`config.yaml` are untouched. E8's owner-timing fills are not a report (they change the desk's fills), so they keep
their real live date.

Story REH1j (the full dry run, 24 Oct): such a step is recorded `not_live`, as the real day records it, with what it
did kept beside it under `exercised`, so it never counts as a problem of the day; a step whose command fno has not
built yet is `not_built` there and never run (`built_commands`)."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from datetime import date

from ..constants import (
    ENV_FNO_REHEARSAL_NOT_LIVE,
    OWNER_TIMING_STEP,
    STEP_EXERCISED,
    STEP_FAILED,
    STEP_NOT_BUILT,
    STEP_NOT_LIVE,
)
from ..daily.steps import CommandStep
from ..desk.daily_ports import DayStep
from ..desk.daily_steps import StepOutcome
from .built_commands import NOT_BUILT, is_built
from .mode import rehearsal

NOT_LIVE_UNSET = "not live in real runs yet (live_from unset)"
NOT_LIVE_UNTIL = "not live in real runs on {day} (live from {live_from})"
KEPT_REAL = (OWNER_TIMING_STEP,)


def rehearsed_live(live: dict[str, date | None], env: Mapping[str, str] = os.environ):
    """The live dates the run uses, and each step made live for the rehearsal with the line its posts carry."""
    mode = rehearsal(env)
    if mode is None:
        return live, {}
    notes = {name: (NOT_LIVE_UNSET if real is None else NOT_LIVE_UNTIL.format(day=mode.day, live_from=real))
             for name, real in live.items() if name not in KEPT_REAL and (real is None or mode.day < real)}  # fmt: skip
    return {**live, **dict.fromkeys(notes, mode.day)}, notes


def rehearsed_date(key: str, real: date | None, env: Mapping[str, str] = os.environ) -> date | None:
    """One `daily.live_from` date as the daily run's root sees it (story REH1o): a child that checks its own live date
    (G13's issuers) issues on the replayed day its step was made live for; a real run gets `real` unchanged."""
    return rehearsed_live({key: real}, env)[0][key]


def note_this_process(note: str | None) -> None:
    """The not-live line every labelled post of this process carries (story REH1k: one lab edition per process, as
    one daily-run step at a time); None leaves the process as it is."""
    if note is not None:
        os.environ[ENV_FNO_REHEARSAL_NOT_LIVE] = note


def rehearsed_not_live(steps: dict[str, DayStep], notes: Mapping[str, str]) -> dict[str, DayStep]:
    return {name: NotLiveInRealRuns(step, notes[name]) if name in notes else step for name, step in steps.items()}


class NotLiveInRealRuns(DayStep):
    """Runs its step with the note in the environment, so every post of the step's process and its children carries
    it (the label decorators read it); the note is gone once the step ends. Its outcome is the real day's `not_live`,
    with the step's own result under `exercised` and its files kept for the rehearsal's commit."""

    def __init__(self, step: DayStep, note: str, built: Callable[[Sequence[str]], bool] = is_built):
        self.step, self.note, self.built = step, note, built
        self.command = command_of(step)

    def run(self, day: date) -> StepOutcome:
        try:
            arguments = tuple(self.command(day)) if self.command else None
            built = arguments is None or self.built(arguments)
        except Exception as failure:  # noqa: BLE001 - one step's failure never stops the rehearsed day (O1 design 9)
            return StepOutcome(
                {}, self._not_live({"status": STEP_FAILED, "reason": f"{type(failure).__name__}: {failure}"})
            )
        if not built:
            missing = {"status": STEP_NOT_BUILT, "reason": NOT_BUILT.format(command=" ".join(arguments))}
            return StepOutcome({"command": list(arguments)}, self._not_live(missing))
        os.environ[ENV_FNO_REHEARSAL_NOT_LIVE] = self.note
        try:
            done = self.step.run(day)
        finally:
            os.environ.pop(ENV_FNO_REHEARSAL_NOT_LIVE, None)
        return StepOutcome(done.inputs, self._not_live(done.result), done.paths)

    def _not_live(self, exercised: dict) -> dict:
        return {"status": STEP_NOT_LIVE, "reason": self.note, STEP_EXERCISED: exercised}


def command_of(step: DayStep) -> Callable[[date], Sequence[str]] | None:
    """The command a step runs, found through the decorators around it (each keeps its inner step as `step`); None
    for a step that runs no command (a Python step is never checked for being built)."""
    while step is not None:
        if isinstance(step, CommandStep):
            return step.arguments
        step = getattr(step, "step", None)
    return None
