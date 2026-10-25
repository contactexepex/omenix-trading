"""The dashcam's records (story 3.4). Before fills: one decision record per scheduled (session, slot, road, driver
version) and one exit record per position an exit rule closes. After fills: outcome records and NIFTY drift rows.
Never edited: a correction is a new record naming the old one."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date

from ..constants import RECORD_SCHEMA_VERSION, ClosureReason, ExitReason, Outcome, RoadCode
from .accounts import FilledLeg, FillResult
from .codec import CanonicalRecord
from .decisions import Decision
from .safety import LawResult
from .snapshot import ContractKey, SlotQuote


@dataclass(frozen=True)
class WitnessedQuote:
    key: ContractKey
    quote: SlotQuote


@dataclass(frozen=True)
class DecisionRecord(CanonicalRecord):
    session: date
    slot: str
    road: RoadCode
    card_sha256: str
    snapshot_id: str  # empty only when the road had no snapshot to read
    snapshot_sha256: str
    road_closed_by: ClosureReason | None
    decision: Decision
    law_results: tuple[LawResult, ...] = ()
    witnessed: tuple[WitnessedQuote, ...] = ()  # every proposal leg's quote at the snapshot
    inputs: Mapping[str, float | int | str] = field(default_factory=dict)  # e.g. expected move, history sessions
    schema: int = RECORD_SCHEMA_VERSION

    def __post_init__(self):
        if self.decision.session != self.session or self.decision.road != self.road:
            raise ValueError("the record's session and road are its decision's")
        closed = self.decision.outcome == Outcome.ROAD_CLOSED
        if closed != (self.road_closed_by is not None) or (closed and self.decision.reason != self.road_closed_by):
            raise ValueError("a closed road is exactly a road_closed decision with the same reason")
        if not closed and not (self.snapshot_id and self.snapshot_sha256):
            raise ValueError("a decision on an open road names its snapshot")


@dataclass(frozen=True)
class ExitRecord(CanonicalRecord):
    session: date
    slot: str
    position_id: str
    driver_id: str
    road: RoadCode
    exit_reason: ExitReason
    snapshot_id: str
    schema: int = RECORD_SCHEMA_VERSION


@dataclass(frozen=True)
class OutcomeRecord(CanonicalRecord):
    position_id: str
    driver_id: str
    road: RoadCode
    decision_sha256: str  # the sealed decision file the entry rests on
    entry: FillResult
    exit: FillResult
    exit_reason: ExitReason
    gross: float
    costs: float
    net: float
    return_on_risk: float  # net / maximum loss at entry
    slippage_vs_mid: float  # rupees paid against the mids of the filled legs, entry and exit
    is_ticket: bool = False
    corrects: str = ""  # SHA-256 of the record this one corrects, if any
    schema: int = RECORD_SCHEMA_VERSION

    def __post_init__(self):
        if not (self.entry.filled and self.exit.filled):
            raise ValueError("an outcome closes a position that was filled at entry and at exit (or settlement)")


@dataclass(frozen=True)
class DriftRow(CanonicalRecord):
    """The NIFTY diagnostic (story 3.6), never a fill: a filled leg's touch against the same contract at 15:15."""

    session: date
    position_id: str
    leg: FilledLeg
    price_1515: float | None  # the same side's touch in E3's 15:15 capture; None when the leg is absent there
    schema: int = RECORD_SCHEMA_VERSION

    @property
    def unknown(self) -> bool:
        return self.price_1515 is None

    @property
    def drift(self) -> float | None:
        return None if self.unknown else self.price_1515 - self.leg.price
