"""The historical `SnapshotSource` (story MS-SIM-c): one road-session's snapshot built from that day's archived closes.

A leg gets a quote only when it traded that day, its close is not impossible (EDGE1's rule, judged on the closes as one
price a leg, through the pilot's own `impossible_keys`) and its spread bucket has 30 quoted sessions; the quote is then
the close less and plus the chosen scenario's half-spread. Any other leg is an invalid quote: the pilot's gates refuse a
trade that needs it, an exit on it waits. Only that day's chain is read, so nothing after the decision can enter."""

import hashlib
import json
from datetime import datetime, time

from ....models import IST
from ...constants import ClosureReason
from ...contracts.roads import RoadDay
from ...contracts.snapshot import ContractKey, SlotQuote, SlotSnapshot, SnapshotUnavailable
from ...quality.prices import impossible_keys
from ..constants import PracticeRefusal
from ..history.ports import ChainRow, HistoricalChain
from ..spreads.bucket import bucket_of
from ..spreads.model import InsufficientSpreadData, Scenario, SpreadModel
from ..windows import PracticeWindows
from .coverage import Coverage
from .quotes import no_quote, point_quote, practice_quote

CLOSE = time(15, 30)  # the close: the practice slot (7.1 item 4)


class HistoricalRoadSource:
    def __init__(self, chain: HistoricalChain, spreads: SpreadModel, scenario: Scenario, windows: PracticeWindows):
        self.chain, self.spreads, self.scenario, self.windows = chain, spreads, scenario, windows

    def for_road(self, road_day: RoadDay) -> SlotSnapshot:
        return self.build(road_day)[0]

    def build(self, road_day: RoadDay) -> tuple[SlotSnapshot, Coverage]:
        """The snapshot and what it could not price. The road day must be open and its chain still archived."""
        if not road_day.status.open:
            raise SnapshotUnavailable(road_day.status.closed_by, "the road is closed")
        if self.windows.check(road_day.road.code, road_day.session):
            raise SnapshotUnavailable(ClosureReason.CAPTURE_MISSING, str(PracticeRefusal.NOT_IN_DATA_SPEND))
        found = self.chain.day(road_day.road.underlying, road_day.session)
        if found is None or found.index_close is None:
            raise SnapshotUnavailable(ClosureReason.CAPTURE_MISSING, "no archived chain or index close")
        rows = _once([r for r in found.rows if r.expiry in road_day.expiries])
        coverage = Coverage(legs=len(rows))
        quotes = self._quotes(road_day, found.index_close, rows, coverage)
        moment = datetime.combine(road_day.session, CLOSE, tzinfo=IST)
        name = f"practice_{road_day.road.stem}_{road_day.session:%Y%m%d}_{self.scenario}"
        digest = _digest(name, found.index_close, quotes)
        snapshot = SlotSnapshot(road_day.road.code, road_day.session, name, digest, moment, moment, found.index_close,
                                road_day.expiries, quotes)  # fmt: skip
        return snapshot, coverage

    def _quotes(self, road_day: RoadDay, spot: float, rows: list[ChainRow], coverage: Coverage) -> dict:
        traded = {ContractKey(r.expiry, r.strike, r.kind): r for r in rows if r.volume > 0 and r.close > 0}
        points = _point_snapshot(road_day, spot, traded)
        flagged = impossible_keys(points)
        quotes: dict[ContractKey, SlotQuote] = {}
        for row in rows:
            key = ContractKey(row.expiry, row.strike, row.kind)
            if key not in traded:
                coverage.untraded += 1
                quotes[key] = no_quote(row.close or None)
            elif key in flagged:
                coverage.impossible += 1
                quotes[key] = no_quote(row.close)
            else:
                quotes[key] = self._priced(road_day, spot, row, coverage)
        return quotes

    def _priced(self, road_day: RoadDay, spot: float, row: ChainRow, coverage: Coverage) -> SlotQuote:
        bucket = bucket_of(road_day.road.underlying, spot, row.strike, road_day.session, row.expiry)
        found = self.spreads.scenarios(bucket) if bucket else None
        if not found or isinstance(found, InsufficientSpreadData):
            coverage.insufficient[str(bucket)] += 1
            if isinstance(found, InsufficientSpreadData):
                coverage.short_buckets[str(bucket)] = found.sessions
            return no_quote(row.close)
        quote = practice_quote(row.close, found.half_spread(self.scenario))
        if quote.two_sided:
            coverage.priced += 1
        else:
            coverage.unsellable += 1  # priced, but the bid rounds to nothing: it can be bought, never sold back
        return quote


def _point_snapshot(road_day: RoadDay, spot: float, traded: dict) -> SlotSnapshot:
    moment = datetime.combine(road_day.session, CLOSE, tzinfo=IST)
    return SlotSnapshot(road_day.road.code, road_day.session, "points", "", moment, moment, spot, road_day.expiries,
                        {k: point_quote(r.close) for k, r in traded.items()})  # fmt: skip


def _digest(name: str, spot: float, quotes: dict) -> str:
    body = sorted(
        (str(k.expiry), k.strike, str(k.kind), q.bid, q.ask, q.bid_qty, q.ask_qty, q.last, q.valid)
        for k, q in quotes.items()
    )
    return hashlib.sha256(json.dumps([name, spot, body], sort_keys=True).encode()).hexdigest()


def _once(rows: list[ChainRow]) -> list[ChainRow]:
    """One row per contract (the first), so a file that lists a contract twice is not counted twice."""
    return list({(r.expiry, r.strike, r.kind): r for r in reversed(rows)}.values())[::-1]
