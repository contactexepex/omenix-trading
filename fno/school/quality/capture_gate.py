"""The capture gate per road (story 3.5, frozen in MS-P1h before counting): a road counts only when its snapshot passed
on each of the last 10 consecutive trading sessions **and** over 95% of its band's leg observations passed over those
sessions. A failing road stays closed for counting while the others run. Counts only: no strike, price or contract."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from ...research_data.calendar import SessionCalendar
from ...storage.trading_days import is_trading_day
from ..constants import ClosureReason, RoadCode
from ..contracts.roads import RoadCatalogue, RoadDay
from ..contracts.snapshot import SnapshotSource, SnapshotUnavailable
from .gate import LegCounts, RoadQualityGate
from .ports import ListingUnavailable

GATE_SESSIONS = 10
LEG_PERCENT_ABOVE = 95  # strictly over: exactly 95.0% fails
NO_LEGS = LegCounts(0, 0)
ROAD_LINE = (
    "{road} through {through}: snapshots {ok} of {sessions}{reasons}; legs {passed} of {observed} ({share}); "
    "gate {verdict}"
)


@dataclass(frozen=True)
class SessionVerdict:
    session: date
    closure: ClosureReason | None  # None: the snapshot passed
    legs: LegCounts  # no legs are scheduled for a road-session whose snapshot failed


@dataclass(frozen=True)
class RoadGate:
    road: RoadCode
    through: date
    sessions: tuple[SessionVerdict, ...]  # oldest first, the last trading sessions up to `through`

    @property
    def snapshots_passed(self) -> int:
        return sum(1 for verdict in self.sessions if verdict.closure is None)

    @property
    def legs(self) -> LegCounts:
        return LegCounts(sum(v.legs.observed for v in self.sessions), sum(v.legs.passed for v in self.sessions))

    @property
    def passed(self) -> bool:
        return (
            len(self.sessions) == GATE_SESSIONS
            and self.snapshots_passed == len(self.sessions)
            and self.legs.passed * 100 > LEG_PERCENT_ABOVE * self.legs.observed
        )

    def line(self) -> str:
        legs = self.legs
        closures = Counter(v.closure for v in self.sessions if v.closure)
        counted = ", ".join(f"{reason} {count}" for reason, count in sorted(closures.items()))
        share = f"{100 * legs.passed / legs.observed:.2f}%" if legs.observed else "no legs"
        return ROAD_LINE.format(
            road=self.road, through=self.through, ok=self.snapshots_passed, sessions=len(self.sessions),
            reasons=f" ({counted})" if counted else "", passed=legs.passed, observed=legs.observed, share=share,
            verdict="open" if self.passed else "closed",
        )  # fmt: skip


class CaptureGateReport:
    def __init__(self, calendar: SessionCalendar, catalogue: RoadCatalogue, snapshots: SnapshotSource,
                 gate: RoadQualityGate):  # fmt: skip
        self.calendar, self.catalogue, self.snapshots, self.gate = calendar, catalogue, snapshots, gate

    def build(self, through: date) -> tuple[RoadGate, ...]:
        """Every road's gate over the last `GATE_SESSIONS` trading sessions up to and including `through`."""
        sessions = self._last_sessions(through)
        days = {session: self.catalogue.day(session) for session in sessions}
        roads = [road_day.road.code for road_day in days[sessions[-1]]]
        return tuple(
            RoadGate(road, through, tuple(self._verdict(session, road, days[session]) for session in sessions))
            for road in roads
        )

    def lines(self, through: date) -> list[str]:
        return [road_gate.line() for road_gate in self.build(through)]

    def _last_sessions(self, through: date) -> list[date]:
        """Trading days only (A7's regular and special sessions; a muhurat-only evening is not one)."""
        sessions, day = [], through
        while len(sessions) < GATE_SESSIONS:
            if is_trading_day(self.calendar, day):
                sessions.insert(0, day)
            day -= timedelta(days=1)
        return sessions

    def _verdict(self, session: date, road: RoadCode, road_days: tuple[RoadDay, ...]) -> SessionVerdict:
        road_day = next(d for d in road_days if d.road.code == road)
        if not road_day.status.open:
            return SessionVerdict(session, road_day.status.closed_by, NO_LEGS)
        try:
            snapshot = self.snapshots.for_road(road_day)
        except SnapshotUnavailable as unavailable:
            return SessionVerdict(session, unavailable.reason, NO_LEGS)
        status = self.gate.check(road_day, snapshot)
        if not status.open:
            return SessionVerdict(session, status.closed_by, NO_LEGS)
        try:
            return SessionVerdict(session, None, self.gate.legs(road_day, snapshot))
        except ListingUnavailable:  # an unreadable listing file: the legs cannot be scheduled, so the session fails
            return SessionVerdict(session, ClosureReason.EXPIRY_MISMATCH, NO_LEGS)
