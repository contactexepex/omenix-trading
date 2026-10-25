"""The practice report's data (story MS-SIM-d3): what a run found, per scenario and driver, with what it could not
price. Nothing here ranks, licenses or recommends; the lines it renders (`render.py`) all carry the practice label."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from ...constants import RoadCode
from ..source.coverage import Coverage
from ..spreads.model import Scenario


@dataclass
class DriverResult:
    """One driver in one scenario, over the sessions of the window. Counts come from the fleet's own sealed decisions
    and counts files; `net` is the account trades only (`account_net`), tickets never in rupees."""

    scheduled: int = 0
    eligible: int = 0
    fillable: int = 0
    executed: int = 0
    outcomes: Counter = field(default_factory=Counter)  # `outcome:reason` (or the outcome alone) -> decisions
    closed_trades: int = 0
    net: float = 0.0


@dataclass
class RoadDayCoverage:
    """What one road-session's snapshot could not price (the source's `Coverage`), so a result is not read as a full
    chain: untraded and impossible legs are the data's; insufficient is the spread model's."""

    session: date
    road: RoadCode
    legs: int
    priced: int
    untraded: int
    impossible: int
    unsellable: int
    insufficient: int

    @classmethod
    def of(cls, session: date, road: RoadCode, found: Coverage) -> "RoadDayCoverage":
        return cls(session, road, found.legs, found.priced, found.untraded, found.impossible, found.unsellable,
                   sum(found.insufficient.values()))  # fmt: skip

    @property
    def impossible_share(self) -> float:
        return self.impossible / self.legs if self.legs else 0.0


@dataclass
class ScenarioResult:
    drivers: dict[str, DriverResult] = field(default_factory=dict)
    sessions_run: int = 0
    failed_margin: int = 0  # decisions on which law 3 failed, whether refused or ticketed (an account limit)

    def driver(self, driver_id: str) -> DriverResult:
        return self.drivers.setdefault(driver_id, DriverResult())


@dataclass
class PracticeReport:
    first: date
    last: date
    roads: tuple[RoadCode, ...]
    scenarios: dict[Scenario, ScenarioResult] = field(default_factory=dict)
    coverage: list[RoadDayCoverage] = field(default_factory=list)
    insufficient_buckets: Counter = field(default_factory=Counter)  # bucket text -> legs left without a quote
    sessions_without_roads: int = 0
    sessions_without_span: int = 0  # sessions before the SPAN archive began, refused by name and not run
    margin_label: str = ""  # built from the factor row the run used
    short_buckets: dict[str, int] = field(default_factory=dict)  # bucket text -> recorded sessions, each under 30
