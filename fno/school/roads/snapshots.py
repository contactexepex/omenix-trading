"""The slot snapshot of an open road, from the verified capture (story 3.1)."""

from ..contracts.roads import RoadDay
from ..contracts.snapshot import SlotSnapshot, SnapshotUnavailable
from .capture import CaptureProblem, CaptureReader


class RecordedSnapshotSource:
    def __init__(self, captures: CaptureReader):
        self.captures = captures

    def for_road(self, road_day: RoadDay) -> SlotSnapshot:
        if not road_day.status.open:
            raise SnapshotUnavailable(road_day.status.closed_by, "the road is closed")
        try:
            return self.captures.read(road_day.road, road_day.session).snapshot()
        except CaptureProblem as problem:
            raise SnapshotUnavailable(problem.reason, problem.detail) from problem
