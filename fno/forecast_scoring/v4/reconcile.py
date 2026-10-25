"""Before a confirmatory look, every scheduled AI slot-day must be settled (ChatGPT review 127, response 213;
agreed with G11). G11 writes one v4 record row for each registered hybrid or ai_team slot, question and session day
once the day settles, whatever the outcome (ok, or a definitive miss such as not_fired or no_submission). A session
from the slot's counted start to the look's date with no row (a sealed answer never collected, a collect that died, an
audit still open) is unsettled, and the look refuses rather than record a provisional miss. The rules slot's gaps stay
ordinary misses. This one rule replaces the open-audits file (judge 209): an open audit is a day without a row. A
book stopped by its stop rule writes `stopped` rows, which settle their days like any other status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from ...constants import V4_DAY_SYSTEM_LATE, V4_SLOT_AI, V4_SLOT_HYBRID
from .days import V4DaySource
from .inputs import V4ForecastSource
from .records import SlotRegistry

AI_SLOTS = (V4_SLOT_HYBRID, V4_SLOT_AI)
UNSETTLED = ("a look on {look} needs every AI slot-day settled: {count} without a record row, the earliest {day} "
             "({question}, {slot})")  # fmt: skip


class LookBlocked(RuntimeError):
    """A confirmatory look refused because an AI slot-day up to its date is not settled; nothing was recorded."""


@dataclass(frozen=True)
class SlotDay:
    day: date
    question: str
    slot: str


class AiSlotDays:
    """`sessions(first, last)`: the v4 scored sessions in [first, last] that are not system_late."""

    def __init__(self, forecasts: V4ForecastSource, registry: SlotRegistry,
                 sessions: Callable[[date, date], list[date]]):  # fmt: skip
        self.forecasts, self.registry, self.sessions = forecasts, registry, sessions

    def unsettled(self, freeze_day: date, look_day: date) -> list[SlotDay]:
        missing = []
        for (question, slot), registration in self.registry.registered().items():
            if slot not in AI_SLOTS:
                continue
            held = self.forecasts.values(question, registration.forecaster)  # a row of any status settles the day
            start = max(registration.effective_start, freeze_day + timedelta(days=1))
            missing += [SlotDay(d, question, slot) for d in self.sessions(start, look_day) if d not in held]
        return sorted(missing, key=lambda s: (s.day, s.question, s.slot))


def require_reconciled(unsettled: list[SlotDay], look_day: date) -> None:
    if unsettled:
        first = unsettled[0]
        raise LookBlocked(UNSETTLED.format(look=look_day, count=len(unsettled), day=first.day,
                                           question=first.question, slot=first.slot))  # fmt: skip


def sessions_not_late(is_session: Callable[[date], bool], days: V4DaySource) -> Callable[[date, date], list[date]]:
    """The v4 scored sessions in [first, last] without a system_late label (G10: out for every family)."""

    def sessions(first: date, last: date) -> list[date]:
        late = {d for d, label in days.labels().items() if label.label == V4_DAY_SYSTEM_LATE}
        span = (first + timedelta(days=i) for i in range((last - first).days + 1))
        return [d for d in span if is_session(d) and d not in late]

    return sessions
