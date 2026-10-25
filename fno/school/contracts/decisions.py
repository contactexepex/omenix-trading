"""Driver decisions (story 3.2): a frozen card, its proposal and the one outcome every scheduled road decision gets."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable

from ..constants import REASONS_BY_OUTCOME, SIDES, DriverRole, ExitReason, Outcome, RoadCode
from .roads import RoadDay
from .snapshot import ContractKey, SlotSnapshot


@dataclass(frozen=True)
class LegSpec:
    key: ContractKey
    side: str  # fno.constants SIDE_BUY or SIDE_SELL
    lots: int

    def __post_init__(self):
        if self.side not in SIDES or self.lots < 1:
            raise ValueError("a leg needs a buy or sell side and at least one lot")


@dataclass(frozen=True)
class Proposal:
    structure: str  # a structure code (fno.constants STRUCTURES or a card's own)
    legs: tuple[LegSpec, ...]
    lot: int  # units per lot, from the road day's dated lot
    net_premium: float  # rupees for all units: positive is a credit received, negative a debit paid
    max_loss: float  # rupees, every charge and pad included (C2's model)
    costs: float  # rupees: modelled entry and worst exit charges plus pads, inside `max_loss`
    score: float  # the card's frozen ranking score

    def __post_init__(self):
        if not self.legs or self.lot < 1 or self.max_loss <= 0 or not 0 <= self.costs <= self.max_loss:
            raise ValueError("a proposal needs legs, a lot, a positive maximum loss and costs inside it")


@dataclass(frozen=True)
class DriverCard:
    code: str  # e.g. "CS1", "REF", "N0"
    version: str
    family: str
    role: DriverRole
    roads: tuple[RoadCode, ...]
    band_steps: int  # strikes within this many steps of the money: the road's leg observations (story 3.5)
    parameters: Mapping[str, float | int | str] = field(default_factory=dict)
    card_sha256: str = ""  # of the frozen card file; empty only in tests of an unfrozen draft

    @property
    def driver_id(self) -> str:
        return f"{self.code}@{self.version}"


@dataclass(frozen=True)
class SpotPoint:
    session: date
    spot: float  # the road's recorded 15:00 spot (Groww's chain), never a close read from elsewhere


@dataclass(frozen=True)
class OpenPosition:
    position_id: str
    driver_id: str
    road: RoadCode
    structure: str  # C2's bucket map reads it
    legs: tuple[LegSpec, ...]
    lot: int
    opened: date
    entry_net: float  # rupees: credit positive, debit negative, after charges
    max_loss: float


_WITH_PROPOSAL = (Outcome.TRADE, Outcome.TICKET, Outcome.REFUSED)  # a refusal keeps the proposal the laws refused


@dataclass(frozen=True)
class Decision:
    driver_id: str
    road: RoadCode
    session: date
    outcome: Outcome
    reason: str = ""  # a code from REASONS_BY_OUTCOME[outcome]; empty only for a trade
    proposal: Proposal | None = None

    def __post_init__(self):
        if self.reason not in REASONS_BY_OUTCOME[self.outcome]:
            raise ValueError(f"reason {self.reason!r} does not belong to outcome {self.outcome}")
        if (self.outcome in _WITH_PROPOSAL) != (self.proposal is not None):
            raise ValueError("a trade, ticket or refusal carries its proposal; no other outcome does")


@runtime_checkable
class Driver(Protocol):
    card: DriverCard

    def decide(self, road_day: RoadDay, snapshot: SlotSnapshot, history: tuple[SpotPoint, ...],
               positions: tuple[OpenPosition, ...]) -> Decision:  # fmt: skip
        """One decision for this road and session from the snapshot and earlier sessions only (no look-ahead)."""

    def review_exit(self, position: OpenPosition, snapshot: SlotSnapshot,
                    history: tuple[SpotPoint, ...]) -> ExitReason | None:  # fmt: skip
        """The card's exit rule reached at this slot, or None; prices it cannot judge (no valid quote) never fire."""
