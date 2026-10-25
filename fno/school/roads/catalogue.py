"""The five roads of a trading session (story 3.1), each open or closed with exactly one reason.

A road is read in the story's order and stops at the first fault: capture missing, incomplete, out of window, hash
mismatch (all in `CaptureReader`), then expiry mismatch against NSE's listing, then lot not found. The quality gate
adds the last reason, impossible prices, once it sees the quotes."""

from collections.abc import Sequence
from datetime import date

from ...research_data.calendar import SessionCalendar
from ...storage.trading_days import is_trading_day
from ..constants import ClosureReason
from ..contracts.roads import OPEN, ROADS, Road, RoadDay, RoadStatus
from ..quality.rules import expiry_problem
from .capture import CaptureProblem, CaptureReader
from .ports import ExpirySource, ExpiryUnavailable, LotProblem, LotSource


class RecordedRoadCatalogue:
    def __init__(self, calendar: SessionCalendar, captures: CaptureReader, expiries: ExpirySource, lots: LotSource,
                 roads: Sequence[Road] = ROADS):  # fmt: skip
        self.calendar, self.captures, self.expiries, self.lots, self.roads = calendar, captures, expiries, lots, roads

    def day(self, session: date) -> tuple[RoadDay, ...]:
        """Every road with its verdict; nothing on a holiday, a weekend or a muhurat-only day (A7's calendar, which
        raises outside the years it covers: a session is never guessed)."""
        if not is_trading_day(self.calendar, session):
            return ()
        return tuple(self._road_day(road, session) for road in self.roads)

    def _road_day(self, road: Road, session: date) -> RoadDay:
        try:
            capture = self.captures.read(road, session)
            steps = capture.strike_steps()
        except CaptureProblem as problem:
            return _closed(road, session, problem.reason)
        try:
            expected = self.expiries.expected(road, session)
        except ExpiryUnavailable:
            return _closed(road, session, ClosureReason.EXPIRY_MISMATCH)  # unconfirmed expiries never open a road
        if expiry_problem(capture.expiries, expected):
            return _closed(road, session, ClosureReason.EXPIRY_MISMATCH)
        lot = self.lots.lot(road.underlying, session, capture.expiries)
        if isinstance(lot, LotProblem):
            return _closed(road, session, lot.reason)
        return RoadDay(road, session, capture.expiries, lot, steps[capture.expiries[0]], OPEN, steps)


def _closed(road: Road, session: date, reason: ClosureReason) -> RoadDay:
    return RoadDay(road, session, (), None, None, RoadStatus(reason))
