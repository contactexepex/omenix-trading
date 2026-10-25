"""The drivers' spot history for a practice run (story MS-SIM-d1; `SpotHistory` of the fleet, story 3.2): the road's
index closes on the trading sessions strictly before the session, never the session itself or later. A session whose
chain or close is not archived adds no point, as a recorded session without a usable capture adds none in the pilot."""

from datetime import date, timedelta

from ....research_data.calendar import SessionCalendar
from ...contracts.decisions import SpotPoint
from ...contracts.roads import Road
from ..history.ports import HistoricalChain

LOOKBACK_DAYS = 60  # calendar days: a little over 40 sessions, past the longest window a card reads


class ChainSpotHistory:
    def __init__(self, chain: HistoricalChain, calendar: SessionCalendar, lookback_days: int = LOOKBACK_DAYS):
        self.chain, self.calendar, self.lookback_days = chain, calendar, lookback_days

    def spots(self, road: Road, session: date) -> tuple[SpotPoint, ...]:
        first, last = session - timedelta(days=self.lookback_days), session - timedelta(days=1)
        points = []
        for day in self.calendar.sessions(first, last):
            found = self.chain.day(road.underlying, day)
            if found is not None and found.index_close:
                points.append(SpotPoint(day, found.index_close))
        return tuple(points)
