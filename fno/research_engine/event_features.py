"""F3 (story B1): a scheduled event inside the holding window, as known on the decision day."""

from __future__ import annotations

from datetime import date

from ..constants import FEATURE_EVENT_IN_WINDOW
from ..research_data.events import in_window
from .features import DecisionContext, Feature, ResearchData


class ScheduledEventInWindow(Feature):
    """F3: true if an event known on the decision day (story A6's `in_window`: scheduled, announced by then, a moved
    meeting at the date known then, never an unscheduled one) falls after the entry day and on or before the exit
    day."""

    name = FEATURE_EVENT_IN_WINDOW

    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> bool:
        return bool(in_window(list(data.events), decision_day, context.entry_day, context.exit_day))
