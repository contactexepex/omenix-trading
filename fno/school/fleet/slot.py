"""The slot's roads (story MS-P1j; order: roads, gate): each catalogued road of the session is open with its verified
snapshot, or closed with exactly one reason and, when known, a plain detail. A road the catalogue opened can still be
closed by its snapshot source or by the quality gate."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ..constants import ClosureReason, RoadCode
from ..contracts.roads import RoadCatalogue, RoadDay, RoadStatus
from ..contracts.snapshot import SlotSnapshot, SnapshotSource, SnapshotUnavailable
from ..execution.quote_rules import LIVE, QuoteRules

UNMEASURED = "a quote with no measured displayed size"


class QualityGate(Protocol):
    def check(self, road_day: RoadDay, snapshot: SlotSnapshot) -> RoadStatus: ...


@dataclass(frozen=True)
class OpenRoad:
    road_day: RoadDay
    snapshot: SlotSnapshot


@dataclass(frozen=True)
class ClosedRoad:
    road_day: RoadDay
    reason: ClosureReason
    detail: str = ""
    snapshot: SlotSnapshot | None = None  # the snapshot the gate closed, when one was read


@dataclass(frozen=True)
class SlotRoads:
    open: tuple[OpenRoad, ...]
    closed: tuple[ClosedRoad, ...]

    @property
    def marks(self) -> dict[RoadCode, SlotSnapshot]:
        """The open roads' snapshots: what positions are marked and C2's caps priced at."""
        return {road.road_day.road.code: road.snapshot for road in self.open}

    @property
    def scheduled(self) -> tuple[RoadDay, ...]:
        return tuple(r.road_day for r in (*self.open, *self.closed))

    def only(self, codes) -> "SlotRoads":
        """The roads among `codes` (a card's own roads), in the same order."""
        keep = set(codes)
        return SlotRoads(tuple(r for r in self.open if r.road_day.road.code in keep),
                         tuple(r for r in self.closed if r.road_day.road.code in keep))  # fmt: skip


def plan_slot(session: date, catalogue: RoadCatalogue, snapshots: SnapshotSource, gate: QualityGate,
              rules: QuoteRules = LIVE) -> SlotRoads:  # fmt: skip
    """`rules`: d's quote rules. Live (every pilot root), a road whose capture holds a quote with no measured size
    closes as `sizes_not_measured` (judge 506); only the practice rules (the simulator's root) let it through, for
    MS-P1d's practice laws to judge each quote."""
    opened, closed = [], []
    for road_day in catalogue.day(session):
        if not road_day.status.open:
            closed.append(ClosedRoad(road_day, road_day.status.closed_by, road_day.status.detail))
            continue
        try:
            snapshot = snapshots.for_road(road_day)
        except SnapshotUnavailable as unavailable:
            closed.append(ClosedRoad(road_day, unavailable.reason, str(unavailable)))
            continue
        if not rules.practice and not all(quote.sizes_measured for quote in snapshot.quotes.values()):
            closed.append(ClosedRoad(road_day, ClosureReason.SIZES_NOT_MEASURED, UNMEASURED, snapshot))
            continue  # the fleet is live: it never trades on a quote with no measured size (judge 506)
        status = gate.check(road_day, snapshot)
        if status.open:
            opened.append(OpenRoad(road_day, snapshot))
        else:
            closed.append(ClosedRoad(road_day, status.closed_by, status.detail, snapshot))
    return SlotRoads(tuple(opened), tuple(closed))
