"""A practice window (story MS-SIM-d3, criterion 16): the roads and dates a run asks for, checked against DATA_SPEND
before any session is read. A road DATA_SPEND does not list as spent or exposed, or a date outside its allowed days,
refuses the whole window by name; nothing is read and no record is written."""

from dataclasses import dataclass
from datetime import date

from ....research_data.calendar import SessionCalendar
from ...constants import RoadCode
from ..constants import PracticeRefusal
from ..windows import PracticeWindows


class WindowRefused(ValueError):
    """The window asks for a road or a day that is not spent or exposed data."""

    def __init__(self, road: RoadCode, day: date, reason: PracticeRefusal):
        super().__init__(f"{reason}: {road} on {day}")
        self.road, self.day, self.reason = road, day, reason


@dataclass(frozen=True)
class RunWindow:
    first: date
    last: date
    roads: tuple[RoadCode, ...]

    def __post_init__(self):
        if self.last < self.first or not self.roads:
            raise ValueError("a window needs roads and a last day on or after its first")

    def check(self, windows: PracticeWindows) -> None:
        """Raises `WindowRefused` naming the first road and day that may not be practised."""
        for road in self.roads:
            for day in (self.first, self.last):
                if refusal := windows.check(road, day):
                    raise WindowRefused(road, day, refusal)

    def sessions(self, calendar: SessionCalendar) -> list[date]:
        return [d for d in calendar.sessions(self.first, self.last) if calendar.session_kind(d) == "regular"]
