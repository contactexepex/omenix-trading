"""The AI books' decision timetable (story F1t), `config.yaml` `ai_books.decision_timing`, "proposed until S1" like
E3's `desk.timetable`: the last moment a fire may start, the receipt deadline (a commitment counts only if on the
remote then), when the reveal may start, and the reveal deadline. Refused at load unless strictly in this order and
before E3's decision deadline, which is the promotion deadline (a run committed later is late by E3's rule)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from ..ai.observed_receipts import GRACE
from ..ai.remote_observer import LS_REMOTE_SECONDS
from ..desk.timetable import Timetable
from ..models import IST
from .fire import FireTiming
from .outcome import Deadlines

ORDER = ("latest_fire", "receipt_deadline", "reveal_from", "reveal_deadline")


class DecisionTimingError(ValueError):
    """`ai_books.decision_timing` is missing a time or its times are out of order; the message names the key."""


@dataclass(frozen=True)
class DecisionTiming:
    latest_fire: time
    receipt_deadline: time
    reveal_from: time
    reveal_deadline: time
    promotion_deadline: time  # E3's `desk.timetable.decision_deadline`: a run committed later is late

    def at(self, day: date, moment: time) -> datetime:
        return datetime.combine(day, moment, IST)

    def late_at(self, day: date) -> datetime:
        return self.at(day, self.promotion_deadline)

    def deadlines(self, day: date) -> Deadlines:
        return Deadlines(self.at(day, self.receipt_deadline), self.at(day, self.reveal_deadline))

    def fire_timing(self, day: date) -> FireTiming:
        return FireTiming(*(self.at(day, t) for t in (self.latest_fire, self.receipt_deadline, self.reveal_from)))


def decision_timing_from_config(cfg: dict, desk: Timetable) -> DecisionTiming:
    raw = (cfg.get("ai_books") or {}).get("decision_timing") or {}
    times = []
    for name in ORDER:
        try:
            times.append(time.fromisoformat(str(raw[name])))
        except KeyError:
            raise DecisionTimingError(f"config.yaml ai_books.decision_timing.{name} is missing") from None
        except ValueError:
            raise DecisionTimingError(f"config.yaml ai_books.decision_timing.{name} is not a time") from None
    for (first, earlier), (second, later) in zip(zip(ORDER, times), zip(ORDER[1:], times[1:])):
        if not earlier < later:
            raise DecisionTimingError(f"ai_books.decision_timing.{first} must be before {second}")
    last_reading = datetime.combine(date.min, times[-1]) + GRACE + timedelta(seconds=LS_REMOTE_SECONDS)
    if not last_reading.time() < desk.decision_deadline:
        raise DecisionTimingError(
            "ai_books.decision_timing.reveal_deadline plus the last reading's grace "
            f"({int((GRACE + timedelta(seconds=LS_REMOTE_SECONDS)).total_seconds())} s) must be before "
            "desk.timetable.decision_deadline: the collection needs time to commit"
        )
    return DecisionTiming(*times, desk.decision_deadline)
