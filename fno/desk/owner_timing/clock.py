"""When an order fills (story E8 rules 2 and 8): the first 15-minute mark at or after the order time T plus R.

A mark after 15:25 moves the fill to the next session's open plus R; "next session" is A7's calendar, never a
muhurat-only day (it has no 09:15 mark). A session the owner is away (by the availability sealed before T) moves the
fill one session further. An entry is valid only until its first available session: a second away session misses it.
An exit is never dropped and keeps moving, and is retried at every later mark until it fills. E4's own view fills at
the execution snapshot of the decision day."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta

from ...constants import SESSION_MUHURAT
from ...intraday.slots import FIRST_MARK, marks
from ...models import IST
from ...research_data.calendar import SessionCalendar
from .availability import Availability
from .outcomes import ENTRY, MISSED_OWNER_AWAY, DueMark, Missed

LAST_FILL_MARK = time(15, 25)  # a due mark after this moves to the next session (design 03 line 97)
ENTRY_AWAY_MOVES = 1  # an entry may move past one away session, never two (rule 8)


class FillClock(ABC):
    @abstractmethod
    def due(self, order_time: datetime, kind: str) -> DueMark | Missed:
        """The mark an order sent at `order_time` (time zone aware) fills at, or why it misses."""


class OwnerTimingClock(FillClock):
    def __init__(self, reaction_minutes: int, calendar: SessionCalendar, availability: Availability):
        self.reaction = timedelta(minutes=reaction_minutes)
        self.calendar, self.availability = calendar, availability

    def due(self, order_time: datetime, kind: str) -> DueMark | Missed:
        day = order_time.astimezone(IST).date()
        mark = self._first_mark(day, order_time + self.reaction) if self._fill_session(day) else None
        if mark is None:
            day = self._next_fill_session(day)
            mark = self._open_mark(day)
        moves = 0
        while self.availability.away(day, order_time):
            if kind == ENTRY and moves == ENTRY_AWAY_MOVES:
                return Missed(MISSED_OWNER_AWAY)
            moves += 1
            day = self._next_fill_session(day)
            mark = self._open_mark(day)
        return DueMark(day, mark, moves)

    def marks_from(self, due: DueMark, order_time: datetime, until: datetime) -> Iterator[datetime]:
        """An exit's due mark and every following mark up to `until`, on the sessions the owner is not away (rule 7: a
        pending exit is retried at each following mark, never dropped)."""
        day = due.session
        while datetime.combine(day, FIRST_MARK, IST) <= until:
            if day == due.session or not self.availability.away(day, order_time):
                yield from (m for m in marks(day) if (day != due.session or m >= due.mark) and m <= until)
            day = self._next_fill_session(day)

    def _fill_session(self, day: date) -> bool:
        kind = self.calendar.session_kind(day)
        return kind is not None and kind != SESSION_MUHURAT

    def _next_fill_session(self, day: date) -> date:
        day = self.calendar.next_session(day)
        while not self._fill_session(day):
            day = self.calendar.next_session(day)
        return day

    def _open_mark(self, day: date) -> datetime:
        mark = self._first_mark(day, datetime.combine(day, FIRST_MARK, IST) + self.reaction)
        if mark is None:
            raise ValueError(f"reaction time {self.reaction} does not fit in a session")
        return mark

    @staticmethod
    def _first_mark(day: date, target: datetime) -> datetime | None:
        found = next((m for m in marks(day) if m >= target), None)
        return found if found is not None and found.astimezone(IST).time() <= LAST_FILL_MARK else None


class ExecutionSnapshotClock(FillClock):
    """E4's view (`e4_1515`): the decision day's execution snapshot, an unexecutable timing yardstick (rule 10)."""

    def __init__(self, execution_snapshot: time):
        self.execution_snapshot = execution_snapshot

    def due(self, order_time: datetime, kind: str) -> DueMark | Missed:
        day = order_time.astimezone(IST).date()
        return DueMark(day, datetime.combine(day, self.execution_snapshot, IST))
