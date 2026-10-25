"""The common pack's slower inputs (story E2): the NSE session of the day (A7), the official daily closes before the
day (A10/O6) and the scheduled events announced by then (A6). Each offers only what existed as of the day, so a
rebuild after later downloads gives the same pack: closes strictly before the day (the last `CLOSES_KEPT`), events
announced on or before the day. An announcement has a date but no time, so it counts as available only at the end of
its day: one made on the day itself is refused by the 15:00 cutoff."""

from __future__ import annotations

from datetime import date, datetime, time

from ..constants import SESSION_CLOSE_TIME
from ..forecast.closes_source import DailyClosesSource, OfficialCloses
from ..models import IST
from ..research_data.calendar import SessionCalendar
from ..research_data.events import Event
from .pack_inputs import CommonInput, InputBatch
from .pack_items import PackItem

CLOSES_KEPT = 260  # B7's live features need 250 past VIX closes (median) and 21 NIFTY closes (20-day volatility)
END_OF_DAY = time(23, 59, 59)


def _at(day: date, moment: time) -> str:
    return datetime.combine(day, moment, tzinfo=IST).isoformat()


class SessionInput(CommonInput):
    name = "session"

    def __init__(self, calendar: SessionCalendar):
        self.calendar = calendar

    def collect(self, day: date) -> InputBatch:
        kind = self.calendar.session_kind(day)
        return InputBatch((PackItem("session", kind, "NSE session calendar (A7)", _at(day, time(0, 0))),))


class ClosesInput(CommonInput):
    name = "daily_closes"

    def __init__(self, source: DailyClosesSource):
        self.source = source

    def collect(self, day: date) -> InputBatch:
        closes = self.source.closes()
        kept = dict(sorted(closes.through(day).items())[-CLOSES_KEPT:])
        items = tuple(
            PackItem(f"close:{d.isoformat()}", {"nifty": nifty, "vix": vix}, closes.source, _at(d, SESSION_CLOSE_TIME))
            for d, (nifty, vix) in kept.items()
        )
        return InputBatch(items, {"source": closes.source, "table_sha256": OfficialCloses.table_sha256(kept)})


class EventsInput(CommonInput):
    name = "events"

    def __init__(self, events: tuple[Event, ...], source: str):
        self.events, self.source = events, source

    def collect(self, day: date) -> InputBatch:
        known = [e for e in self.events if e.announced_on is not None and e.announced_on <= day and e.day >= day]
        items = tuple(
            PackItem(f"event:{e.day.isoformat()}:{e.kind}", {"scheduled": e.scheduled, "description": e.description},
                     self.source, _at(e.announced_on, END_OF_DAY))
            for e in known
        )  # fmt: skip
        return InputBatch(items, {"source": self.source})
