"""The instructor's frozen types (story MS-INS, part a). The rules that fill them are parts b-d; these types only
refuse a record that could not be true (an attribution that does not add up to its net, a fourth cause, a status
beyond the three 327 allows)."""

import hashlib
import math
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ..constants import RoadCode
from ..contracts.codec import CanonicalRecord
from ..contracts.records import DecisionRecord, ExitRecord, OutcomeRecord
from ..contracts.snapshot import SlotSnapshot

IDENTITY_TOLERANCE_RS = 0.01
MAX_SECONDARY = 2


class Cause(StrEnum):
    """Response 325 section 6.1's 13 root causes, in its numbering."""

    MOVE_BEYOND_RANGE = "move_beyond_range"
    WRONG_DIRECTION = "wrong_direction"
    VOLATILITY_ROSE = "volatility_rose"
    VOLATILITY_COLLAPSED = "volatility_collapsed"
    TIME_DECAY = "time_decay"
    GAP_THROUGH_STOP = "gap_through_stop"
    SCHEDULED_EVENT_SHOCK = "scheduled_event_shock"
    UNSCHEDULED_SHOCK = "unscheduled_shock"
    COSTS_ATE_EDGE = "costs_ate_edge"
    BAD_PRICE_OR_DATA = "bad_price_or_data"
    EXIT_WHIPSAW = "exit_whipsaw"
    NORMAL_NOISE = "normal_noise"
    RULE_BROKEN = "rule_broken"


LOSER_ONLY = frozenset({Cause.GAP_THROUGH_STOP, Cause.COSTS_ATE_EDGE})  # no winner form


class Modifier(StrEnum):
    """Measured with REF and RC1 on the entry road-slot (327 correction 2)."""

    NONE = "none"
    HARD_ROAD = "hard_road"
    BAD_DRIVER = "bad_driver"
    NOT_TESTABLE = "not_testable"


class MapStatus(StrEnum):
    """327 correction 3: these three only. Supported and Confirmed wait for a frozen test family and a second window."""

    EXPLORATORY = "exploratory"
    WATCHING = "watching"
    NOT_ESTABLISHED = "not_established"


class Measure(StrEnum):
    PER_OPPORTUNITY = "per_opportunity"  # trades and tickets: the idea's quality (review 138 section 11)
    EXECUTED = "executed"  # account trades only, shown beside it


class DataFault(StrEnum):
    """Why a closed path cannot be attributed: it is tagged "bad price or data", never given numbers."""

    SEALED_FILE_DAMAGED = "sealed_file_damaged"  # a decisions file whose bytes differ from its seal
    ENTRY_DECISION_MISSING = "entry_decision_missing"
    ENTRY_SEAL_MISMATCH = "entry_seal_mismatch"
    SESSION_NOT_SEALED = "session_not_sealed"  # a trading session held with no sealed decisions file
    SNAPSHOT_MISSING = "snapshot_missing"
    SNAPSHOT_HASH_MISMATCH = "snapshot_hash_mismatch"
    SETTLEMENT_MISSING = "settlement_missing"
    SETTLEMENT_MISMATCH = "settlement_mismatch"
    EXIT_RECORD_MISSING = "exit_record_missing"  # an exit rule closed it, but no exit record was sealed
    EXIT_RECORD_MISMATCH = "exit_record_mismatch"  # the exit record names another driver, road or reason
    NET_MISMATCH_FILLS = "net_mismatch_fills"  # the outcome's net is not its fills' cash (judge 503)


def record_sha256(record: CanonicalRecord) -> str:
    """A record's identity: the SHA-256 of its canonical bytes (what a correction's `corrects` names)."""
    return hashlib.sha256(record.to_bytes()).hexdigest()


def net_matches_fills(outcome: OutcomeRecord) -> bool:
    """The outcome's net is the cash its fills moved, to Rs 0.01; else the residual would hide the gap."""
    return abs(round(outcome.net - (outcome.entry.cash + outcome.exit.cash), 6)) <= IDENTITY_TOLERANCE_RS


@dataclass(frozen=True)
class HeldPath:
    """One closed trade or ticket as the records show it: the outcome, the decision it rests on, the exit record when an
    exit rule closed it, and the road's verified snapshot on every session it was held, entry first."""

    outcome: OutcomeRecord
    entry: DecisionRecord | None
    exit: ExitRecord | None
    snapshots: tuple[SlotSnapshot, ...]
    settlement: float | None  # the index's final settlement price, for a position settled at expiry
    sessions_skipped: int  # held sessions whose road was closed by a sealed closure: their steps merge with the next
    faults: tuple[DataFault, ...]

    def __post_init__(self):
        if [s.session for s in self.snapshots] != sorted({s.session for s in self.snapshots}):
            raise ValueError("a path's snapshots are one per session, in session order")
        if any(s.road != self.outcome.road for s in self.snapshots):
            raise ValueError("a path's snapshots are its own road's")

    @property
    def is_ticket(self) -> bool:
        return self.outcome.is_ticket

    @property
    def attributable(self) -> bool:
        return not self.faults


@dataclass(frozen=True)
class ClosedRead:
    """The closed paths of a range of sessions, and the sessions whose outcomes file could not be read (its bytes
    differ from its seal): those are an alert in every report, never a guess."""

    paths: tuple[HeldPath, ...]
    unreadable: tuple[date, ...]


@dataclass(frozen=True)
class Attribution(CanonicalRecord):
    """Part b's split of one closed path: the Greek components plus the residual, less the costs, is its net."""

    position_id: str
    driver_id: str
    road: RoadCode
    closed_on: date
    is_ticket: bool
    delta: float
    gamma: float
    vega: float
    theta: float
    residual: float
    charges: float
    spread: float  # paid against the mids, entry and exit
    net: float
    steps: int
    steps_merged: int
    iv_unsolved: int
    poor_fit: bool
    rules_sha256: str  # of research/school/INSTRUCTOR_V1.md
    outcome_sha256: str = ""  # the outcome record it was computed on: a later correction of it is re-attributed
    corrects: str = ""  # SHA-256 of the attribution this one replaces

    def __post_init__(self):
        explained = self.delta + self.gamma + self.vega + self.theta + self.residual - self.costs
        if not abs(round(explained - self.net, 6)) <= IDENTITY_TOLERANCE_RS:  # rounded: noise is not a paisa; NaN fails
            raise ValueError("the components less the costs must add up to the net")
        if min(self.steps, self.steps_merged, self.iv_unsolved) < 0 or not self.rules_sha256:
            raise ValueError("counts cannot be negative and the record names its rules")

    @property
    def costs(self) -> float:
        return self.charges + self.spread


@dataclass(frozen=True)
class Classification(CanonicalRecord):
    """Part c's verdict on one closed path: one primary cause (None: unclassified) and up to two secondary. A winner
    (net >= 0) reads each cause in its winner form ("volatility fell" for cause 3), so the sign of `net` is the form."""

    position_id: str
    driver_id: str
    road: RoadCode
    closed_on: date
    is_ticket: bool
    net: float
    primary: Cause | None
    secondary: tuple[Cause, ...]
    not_testable: tuple[Cause, ...]
    modifier: Modifier
    rules_sha256: str
    corrects: str = ""  # SHA-256 of the classification this one replaces (a re-check, or a corrected outcome)
    outcome_sha256: str = ""  # the outcome record it was classified on

    def __post_init__(self):
        causes = self.causes
        if len(self.secondary) > MAX_SECONDARY or (self.secondary and self.primary is None):
            raise ValueError("at most two secondary causes, and only beside a primary one")
        if len(causes) != len(set(causes)) or set(causes) & set(self.not_testable):
            raise ValueError("a cause appears once, and never both tagged and not testable")
        if self.winner and set(causes) & LOSER_ONLY:
            raise ValueError("gap through stop and costs ate the edge have no winner form")
        if not self.rules_sha256:
            raise ValueError("the record names its rules")

    @property
    def winner(self) -> bool:
        return self.net >= 0

    @property
    def causes(self) -> tuple[Cause, ...]:
        return ((self.primary,) if self.primary else ()) + self.secondary


@dataclass(frozen=True)
class PairedRow(CanonicalRecord):
    """Part d's comparison of one driver version with one control over a range of counted sessions."""

    driver_id: str
    control_id: str
    measure: Measure
    first: date | None
    last: date | None
    sessions: int  # series points: one per session, however many roads it had
    road_slots: int
    driver_abstentions: int
    control_abstentions: int
    unavailable: int
    after_cut: int  # closed pairs after the first open one: shown, never part of the series
    mean: float | None
    bound: float | None  # one-sided 95% Student-t lower bound on the batch means; None below two whole batches
    batch: int  # sessions per batch: the longer of the two cards' frozen holds
    status: MapStatus
    rules_sha256: str
    note: str = ""  # e.g. "too few independent batches", printed beside the status

    def __post_init__(self):
        counts = (self.sessions, self.road_slots, self.driver_abstentions, self.control_abstentions, self.unavailable,
                  self.after_cut)  # fmt: skip
        if min(counts) < 0 or self.batch < 1:
            raise ValueError("counts cannot be negative and a batch holds at least one session")
        if (self.mean is None) != (self.sessions == 0):
            raise ValueError("a mean exactly when the series has a session")
        if (self.bound is not None and self.mean is None) or not all(
            v is None or math.isfinite(v) for v in (self.mean, self.bound)
        ):
            raise ValueError("a bound only beside a mean, and both finite")
        if self.status == MapStatus.WATCHING and not (self.bound is not None and self.bound > 0):
            raise ValueError("watching needs a bound above zero")
        if (self.first is None) != (self.sessions == 0) or (self.last is None) != (self.first is None):
            raise ValueError("a series with sessions names its first and last session")
        if self.first is not None and self.first > self.last:
            raise ValueError("the first session comes before the last")
