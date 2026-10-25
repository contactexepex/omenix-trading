"""From E8's live date on (`config.yaml` `daily.live_from.owner_timing_fills`), the daily run hands entries to the
owner-timing fill and only alerts ordered exits; before it, E4 fills and closes at the execution snapshot as today.
The date is read from each snapshot's (or run's) day, so a rerun of an earlier day keeps that day's rule, and each
decision is handled once, on its own day, by that day's rule: nothing fills twice. No date set: never. Before the
date the step still seals the availability file, so its seal history exists at go-live."""

from __future__ import annotations

from datetime import date

from ...alerts.sender import AlertSender
from ..daily_ports import DayStep
from ..daily_steps import StepOutcome
from ..entries import EntryFiller, EntryOrder, EntryResult
from ..exit_timing import ExitTiming, ImmediateExits
from ..exits import ExitResult
from .step import OwnerTimingStep

SEAL_ALERT = "F&O owner-timing fills {day}: {reason}"


def live(live_from: date | None, day: date) -> bool:
    return live_from is not None and day >= live_from


class LiveFromEntries(EntryFiller):
    def __init__(self, live_from: date | None, before: EntryFiller, after: EntryFiller):
        self.live_from, self.before, self.after = live_from, before, after

    def enter(self, order: EntryOrder, snapshot, journal, checks) -> EntryResult:
        chosen = self.after if live(self.live_from, snapshot.day) else self.before
        return chosen.enter(order, snapshot, journal, checks)


class LiveFromExits(ExitTiming):
    def __init__(self, live_from: date | None, after: ExitTiming):
        self.live_from, self.after, self.before = live_from, after, ImmediateExits()

    def defer(self, book, position, snapshot, journal) -> ExitResult | None:
        chosen = self.after if live(self.live_from, snapshot.day) else self.before
        return chosen.defer(book, position, snapshot, journal)


class LiveFromStep(DayStep):
    """The owner-timing step from the live date; before it, the availability seal only (judge 203 early view 5). A
    failed seal while off blocks nothing but is alerted once, so the first live day never starts without seals unseen
    (O1's review): the daily run alerts only failed or refused steps."""

    def __init__(self, live_from: date | None, step: OwnerTimingStep, alerts: AlertSender):
        self.live_from, self.step, self.alerts = live_from, step, alerts

    def run(self, day: date) -> StepOutcome:
        if live(self.live_from, day):
            return self.step.run(day)
        outcome = self.step.seal_only(day)
        if outcome.result.get("seal_failed"):
            self.alerts.send(SEAL_ALERT.format(day=day, reason=outcome.result["reason"]))
        return outcome
