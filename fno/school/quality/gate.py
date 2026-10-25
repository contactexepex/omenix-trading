"""The quality gate of a road-day (story 3.5): the snapshot a driver is about to see is the one the road said it was,
and its quotes can be priced. A closed road stays closed with its one reason; an open one closes with exactly one."""

from dataclasses import dataclass

from ..constants import ClosureReason
from ..contracts.roads import OPEN, RoadDay, RoadStatus
from ..contracts.snapshot import SlotSnapshot
from .band import DEFAULT_BAND_STEPS, band_keys
from .ports import ListedContracts
from .prices import impossible_keys
from .rules import expiry_problem, window_problem

WRONG_SNAPSHOT = "the snapshot is not the road-day's own: {snapshot} against {road_day}"


@dataclass(frozen=True)
class LegCounts:
    """The scheduled leg observations of one road-session and how many counted (valid, two-sided, not impossible)."""

    observed: int
    passed: int


class RoadQualityGate:
    def __init__(self, listing: ListedContracts, band_steps: int = DEFAULT_BAND_STEPS):
        """`listing`: what NSE listed, the source of the scheduled legs (never the capture)."""
        self.listing, self.band_steps = listing, band_steps

    def check(self, road_day: RoadDay, snapshot: SlotSnapshot) -> RoadStatus:
        """Open, or closed with the first reason found: out of window, expiry mismatch, impossible price. A road the
        catalogue closed keeps its reason."""
        if not road_day.status.open:
            return road_day.status
        if (snapshot.road, snapshot.session) != (road_day.road.code, road_day.session):
            raise ValueError(WRONG_SNAPSHOT.format(snapshot=(snapshot.road, snapshot.session),
                                                   road_day=(road_day.road.code, road_day.session)))  # fmt: skip
        reason = (
            window_problem(snapshot.road, snapshot.session, snapshot.started_at, snapshot.finished_at)
            or expiry_problem(snapshot.expiries, road_day.expiries)
            or (ClosureReason.IMPOSSIBLE_PRICE if self._impossible_in_band(snapshot) else None)
        )
        return RoadStatus(reason) if reason else OPEN

    def legs(self, road_day: RoadDay, snapshot: SlotSnapshot) -> LegCounts:
        """The leg observations of an open road-day. Scheduled: the contracts NSE listed that the recorder takes at this
        spot and that fall in the band of the listed strikes. A scheduled leg the capture lacks is
        observed and not passed. Raises `ListingUnavailable` when the listing cannot be read."""
        listed = self.listing.contracts(road_day.road.underlying, road_day.expiries, road_day.session, snapshot.spot)
        scheduled = band_keys(listed, snapshot.spot, self.band_steps)
        impossible = impossible_keys(snapshot, scheduled)
        passed = sum(1 for key in scheduled if self._counts(snapshot, key) and key not in impossible)
        return LegCounts(len(scheduled), passed)

    @staticmethod
    def _counts(snapshot: SlotSnapshot, key) -> bool:
        quote = snapshot.quote(key)
        return quote is not None and quote.two_sided

    def _impossible_in_band(self, snapshot: SlotSnapshot) -> bool:
        return bool(impossible_keys(snapshot, band_keys(list(snapshot.quotes), snapshot.spot, self.band_steps)))
