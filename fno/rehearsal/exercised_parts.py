"""`quotes_done` in a rehearsal (story REH1j): a quote part whose live key is not live on the replayed day joined the
day only because the rehearsal made its key live (`rehearsed_live`); on the real day it is not a part of the day. So
its result is kept apart under `exercised_parts`, and only the live parts decide the step, by `parts_result`'s own
rule. Chosen in the daily run's composition root; a real run, or a day with every part live, is unchanged."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from datetime import date

from ..constants import EXERCISED_PARTS
from ..daily.quote_parts import QuotePart
from ..daily.quote_steps import parts_result
from ..desk.daily_ports import DayStep
from ..desk.daily_steps import StepOutcome


def rehearsed_quotes_done(step: DayStep, parts: Sequence[QuotePart], notes: Mapping[str, str]) -> DayStep:
    """`notes`: the live keys not live on the replayed day (none outside a rehearsal)."""
    apart = {part.name for part in parts if part.live_key in notes}
    return ExercisedPartsApart(step, apart) if apart else step


class ExercisedPartsApart(DayStep):
    def __init__(self, step: DayStep, names: Collection[str]):
        self.step, self.names = step, frozenset(names)

    def run(self, day: date) -> StepOutcome:
        done = self.step.run(day)
        parts = done.result.get("parts")
        if parts is None:  # the step raised or never reached its parts: its own result stands
            return done
        live = {name: result for name, result in parts.items() if name not in self.names}
        exercised = {name: result for name, result in parts.items() if name in self.names}
        return StepOutcome(done.inputs, {**parts_result(live), EXERCISED_PARTS: exercised}, done.paths)
