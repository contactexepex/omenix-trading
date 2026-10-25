"""What the sections read (story MS-P1g): small ports, so the sections know no store. The join-up (MS-P1j) wires them
to the roads, the dashcam's records, the ticket counts and the driver cards; tests use plain fakes."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ..constants import DriverRole, RoadCode
from ..contracts.roads import RoadDay
from ..contracts.slot_file import SlotRecord
from ..contracts.tickets import OpportunityCounts


@dataclass(frozen=True)
class PlannedTrade:
    """One line of the 08:50 plan, made from yesterday's data with indicative prices; booked at the slot or dropped."""

    driver_id: str
    role: DriverRole
    road: RoadCode
    structure: str  # a structure code such as "PCS"; never a strike or a contract
    worst_loss: float  # rupees, every charge and pad included


class TodayInputs(Protocol):
    def roads(self, session: date) -> tuple[RoadDay, ...]:
        """The roads as the latest completed capture left them, closed ones with their one reason."""

    def plan(self, session: date) -> tuple[PlannedTrade, ...]:
        """The paper trades planned for the session's 15:00 slot."""

    def not_planned(self, session: date) -> tuple[str, ...]:
        """The rule drivers whose plan failed, each "<driver id> (<failure>: <error class>)" (MS-P1j4)."""

    def source(self, session: date) -> date:
        """The session whose 15:00 data the roads and the plan come from (at 08:50, the previous session's)."""


class DayInputs(Protocol):
    def records(self, session: date) -> tuple[SlotRecord, ...]:
        """The session's sealed decision and outcome records (the dashcam's replay reader)."""

    def counts(self, session: date) -> tuple[OpportunityCounts, ...]:
        """Eligible, fillable and executed per road and driver version (story MS-P1f)."""

    def role_of(self, driver_id: str) -> DriverRole:
        """The driver card's role: only rule drivers are shown as trades."""

    def marks(self, session: date) -> tuple[str, ...]:
        """The run's marks on the session's record, shown as written (e.g. a rerun after 15:30: MS-P1j)."""

    def finished(self, session: date) -> bool:
        """True when the session's run sealed its finish (the outcomes and drift files, even empty); false when it
        stopped after the decisions seal (MS-P1j4 round 2, judge 648)."""

    def school_step(self, session: date) -> tuple[str, str] | None:
        """The daily run's `school` step on the session as its committed run log holds it: (status, public reason
        code), or None when the log or the step is missing (MS-P1j4). A log that cannot be read raises."""

    def why(self, session: date) -> tuple[str, ...]:
        """The instructor's lines on the session's closed trades (MS-INS part e), or () without a source. Each starts
        with a driver id and a road and holds the net and cause words only, never a contract, strike or price."""
