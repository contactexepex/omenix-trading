"""The practice quality gate (story MS-SIM-d2; orchestrator, 22 Oct: a new strategy behind the gate interface).

The pilot's `RoadQualityGate` judges a capture: its window (about 14:55-15:10), its expiries against NSE's listing, its
prices. A historical close has no capture window, and the catalogue and the source have already applied the rules that
do carry over (the data window, traded that day, impossible prices, dated lots). So this gate keeps what is left: a
closed road keeps its one reason, and the snapshot must be the road-day's own."""

from ...contracts.roads import OPEN, RoadDay, RoadStatus
from ...contracts.snapshot import SlotSnapshot
from ...quality.gate import WRONG_SNAPSHOT


class PracticeQualityGate:
    def check(self, road_day: RoadDay, snapshot: SlotSnapshot) -> RoadStatus:
        if not road_day.status.open:
            return road_day.status
        if (snapshot.road, snapshot.session) != (road_day.road.code, road_day.session):
            raise ValueError(WRONG_SNAPSHOT.format(snapshot=(snapshot.road, snapshot.session),
                                                   road_day=(road_day.road.code, road_day.session)))  # fmt: skip
        return OPEN
