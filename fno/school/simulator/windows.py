"""Which history may be practised (story MS-SIM, 7.1 item 2): only data DATA_SPEND lists as spent or exposed.

`PRACTICE_WINDOWS` is a frozen allow-list, one entry per road, each naming the register row it rests on. A test reads
`research/DATA_SPEND.md` and fails if any named row is not `spent` or `exposed`, so the list cannot outlive it.
A road with no entry (FINNIFTY and MIDCPNIFTY are not in the register) is refused. A window also ends the day before
`school.first_counted`, so the simulator never reads the closes of a day the pilot will count."""

from dataclasses import dataclass
from datetime import date, timedelta

from ..constants import RoadCode
from .constants import DATA_END, PracticeRefusal


@dataclass(frozen=True)
class RegisterRow:
    """A DATA_SPEND row: its data-set cell starts with `data_set`, its period cell contains `period`."""

    data_set: str
    period: str


@dataclass(frozen=True)
class PracticeWindow:
    first: date
    last: date
    rows: tuple[RegisterRow, ...]  # every one must be spent or exposed


NIFTY_MONTHLY_ROWS = (
    RegisterRow("NIFTY monthly options", "2024-2026"),
    RegisterRow("NIFTY monthly options", "2019-2023"),
)
PRACTICE_WINDOWS = {
    RoadCode.NIFTY_MONTHLY: PracticeWindow(date(2019, 1, 1), DATA_END, NIFTY_MONTHLY_ROWS),
    RoadCode.NIFTY_WEEKLY: PracticeWindow(
        date(2019, 2, 1), date(2026, 10, 9), (RegisterRow("NIFTY weekly options", "Feb 2019 - 9 Oct 2026"),)
    ),
    RoadCode.BANKNIFTY_MONTHLY: PracticeWindow(
        date(2019, 1, 1), DATA_END, (RegisterRow("BANKNIFTY monthly options", "2019 - 20 Oct 2026"),)
    ),
}


class PracticeWindows:
    def __init__(self, first_counted: date | None = None):
        self.first_counted = first_counted

    def last_day(self, road: RoadCode) -> date | None:
        window = PRACTICE_WINDOWS.get(road)
        if window is None:
            return None
        if self.first_counted is None:
            return window.last
        return min(window.last, self.first_counted - timedelta(days=1))

    def check(self, road: RoadCode, session: date) -> PracticeRefusal | None:
        """None when the session may be practised; otherwise `not_in_data_spend`."""
        window, last = PRACTICE_WINDOWS.get(road), self.last_day(road)
        if window is None or last is None or not window.first <= session <= last:
            return PracticeRefusal.NOT_IN_DATA_SPEND
        return None
