"""Weather baseline v0 live, at a session's 15:00 cutoff (story M1): the frozen rule on regular-session closes up to
the previous regular session (judge 129: a muhurat or special session never supplies a close or the VIX), and a
scheduled event announced on or before the day and dated in the next 5 regular sessions (the V6b horizon).

As a forecaster (scored on V6a and V6b) its probability is the share of big-move outcomes among the most recent 750
outcomes resolved before the cutoff that had the same v0 colour (at least 500 resolved, G7's base-rate rule); a colour
absent from that window is missing."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..forecast_v4_rules.baselines import MINIMUM, MISSING, NOT_ELIGIBLE, WINDOW, Value, before
from ..forecast_v4_rules.series import Outcome
from .checklist_v0 import Event, Row, V0Inputs, v0_colour, v0_inputs
from .constants import WeatherColour
from .model import WeatherModel

Horizon = Callable[[date], date | None]  # the last of the 5 regular sessions after a day (None: calendar ends)
INPUTS_MISSING = "its inputs need more closes before the day"
BEYOND_CALENDAR = (
    "the next 5 sessions run past NSE's session calendar, so the scheduled events are unknown: add NSE's next-year "
    "holiday circular rows (story A7)"
)


class ChecklistV0:
    def __init__(self, rows: list[Row], events: list[Event], horizon: Horizon):
        self.rows, self.events, self.horizon = rows, events, horizon
        self.days = [r.day for r in rows]
        self._colours: dict[date, WeatherColour | None] = {}

    def inputs(self, d: date) -> V0Inputs | None:
        return v0_inputs(self.rows, before(self.days, d) - 1)

    def events_ahead(self, d: date) -> list[Event] | None:
        """Scheduled events known on `d` and dated in its next 5 regular sessions; None when the calendar ends."""
        end = self.horizon(d)
        if end is None:
            return None
        return [e for e in self.events if e.announced <= d and d < e.day <= end]

    def unscored_reason(self, d: date) -> str | None:
        """Why v0 has no colour for `d`, in words (None when it has one): never a silent "not scored"."""
        if self.inputs(d) is None:
            return INPUTS_MISSING
        return BEYOND_CALENDAR if self.events_ahead(d) is None else None

    def colour(self, d: date) -> WeatherColour | None:
        if d not in self._colours:
            inputs, events = self.inputs(d), self.events_ahead(d)
            self._colours[d] = None if inputs is None or events is None else v0_colour(inputs, bool(events))
        return self._colours[d]


class ColourBaseRate(WeatherModel):
    """Weather baseline v0 as a forecaster: the colour-conditional share of each horizon's outcomes."""

    def __init__(self, checklist: ChecklistV0, outcomes: dict[int, list[Outcome]]):
        self.checklist = checklist
        self.outcomes = {h: sorted(found, key=lambda o: o.resolved_on) for h, found in outcomes.items()}
        self.resolved = {h: [o.resolved_on for o in found] for h, found in self.outcomes.items()}

    def forecast(self, d: date, horizon: int) -> Value:
        end = before(self.resolved[horizon], d)
        known = self.outcomes[horizon][max(0, end - WINDOW) : end]
        if len(known) < MINIMUM:
            return Value(NOT_ELIGIBLE)
        colour = self.checklist.colour(d)
        same = [o.value for o in known if colour is not None and self.checklist.colour(o.day) == colour]
        return Value.of(sum(same) / len(same), positive=False) if same else Value(MISSING)
