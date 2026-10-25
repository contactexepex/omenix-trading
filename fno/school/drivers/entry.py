"""What a family sees when it looks for a trade (story MS-P1e): the road's day, today's snapshot, the road's earlier
spots and the card's numbers, with the few questions every family asks (days to expiry, expiry window, history
window, expected move). Families return a `Plan` to build, or the no-trade reason."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ...research_data.calendar import CalendarError
from ..constants import NoTradeReason
from ..contracts.decisions import SpotPoint
from ..contracts.roads import RoadDay
from ..contracts.snapshot import SlotSnapshot
from .card_params import CardParams
from .expected_move import ExpectedMove, expected_move
from .history import SpotWindow, spot_window
from .proposals import Plan
from .session_days import TradingCalendar, previous_session

WINDOW_LENGTH_KEY, MAX_WING_STEPS_KEY = "history_sessions", "max_wing_steps"
DTE_MIN_KEY, DTE_MAX_KEY = "dte_min", "dte_max"
EXPECTED_NET_KEY = "expected_net_rs"
MAX_ATM_STEPS = 2  # the ATM strike may sit at most this many strike steps from spot


@dataclass(frozen=True)
class EntryContext:
    road_day: RoadDay
    snapshot: SlotSnapshot
    history: tuple[SpotPoint, ...]
    calendar: TradingCalendar

    @property
    def session(self) -> date:
        return self.snapshot.session

    @property
    def spot(self) -> float:
        return self.snapshot.spot

    def dte(self, expiry: date) -> int:
        return (expiry - self.session).days

    def window(self, length: int) -> SpotWindow | None:
        return spot_window(self.history, self.session, length)

    def move(self, expiry: date) -> ExpectedMove | None:
        return expected_move(self.snapshot, expiry, MAX_ATM_STEPS * self.road_day.strike_step)

    def expiry_in(self, low: int, high: int, first_in_window: bool = False) -> date | None:
        """The nearest recorded expiry `low` to `high` calendar days away; with `first_in_window`, only on the
        first session the expiry is inside the window (EDGE1's entry day)."""
        for expiry in self.snapshot.expiries:
            if low <= self.dte(expiry) <= high:
                return expiry if not first_in_window or self._first_day_in(expiry, high) else None
        return None

    def _first_day_in(self, expiry: date, high: int) -> bool:
        try:
            return (expiry - previous_session(self.calendar, self.session)).days > high
        except CalendarError:
            return False  # the calendar cannot say which session came before: no entry on a guess

    def wing_widths(self, max_steps: int) -> tuple[float, ...]:
        """Wing widths in points, widest first, from `max_steps` strike steps down to one."""
        step = self.road_day.strike_step
        return tuple(step * n for n in range(max_steps, 0, -1))


class Family(Protocol):
    """One card's entry rule: a plan to build, or why there is none."""

    def plan(self, ctx: EntryContext) -> Plan | NoTradeReason: ...


@dataclass(frozen=True)
class Sizing:
    """The plan numbers every card carries: how far the wings may go and the frozen estimate behind the score."""

    max_wing_steps: int
    expected_net_rs: float

    @classmethod
    def from_params(cls, params: CardParams) -> "Sizing":
        return cls(params.whole(MAX_WING_STEPS_KEY), params.number(EXPECTED_NET_KEY))
