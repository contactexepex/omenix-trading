"""The slot snapshot (story 3.1): one road's canonical 15:00 capture as the drivers, laws and fills see it."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from ..constants import ClosureReason, OptionKind, RoadCode
from .roads import RoadDay


@dataclass(frozen=True, order=True)
class ContractKey:
    expiry: date
    strike: float
    kind: OptionKind


@dataclass(frozen=True)
class SlotQuote:
    bid: float | None
    ask: float | None
    bid_qty: int | None
    ask_qty: int | None
    last: float | None
    valid: bool  # A4's rule (`fno/quotes/quote_validity.py`): a usable market, traded that session
    sizes_measured: bool = True  # False: the source holds no displayed size (the simulator's history); sizes stay None

    def __post_init__(self):
        if not self.sizes_measured and (self.bid_qty is not None or self.ask_qty is not None):
            raise ValueError("a quote whose sizes were not measured carries no size")

    @property
    def two_sided(self) -> bool:
        sized = not self.sizes_measured or (bool(self.bid_qty) and bool(self.ask_qty))
        return self.valid and bool(self.bid) and bool(self.ask) and sized

    @property
    def mid(self) -> float | None:
        return (self.bid + self.ask) / 2 if self.two_sided else None


@dataclass(frozen=True)
class SlotSnapshot:
    road: RoadCode
    session: date
    snapshot_id: str
    sha256: str  # of the quote file, checked against its sidecar before this object exists
    started_at: datetime
    finished_at: datetime
    spot: float
    expiries: tuple[date, ...]
    quotes: Mapping[ContractKey, SlotQuote]

    def __post_init__(self):
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ValueError("snapshot times must be time-zone aware")
        if self.finished_at < self.started_at:
            raise ValueError("a snapshot cannot finish before it starts")
        if tuple(sorted(self.expiries)) != self.expiries:
            raise ValueError("expiries must be nearest first")

    def quote(self, key: ContractKey) -> SlotQuote | None:
        return self.quotes.get(key)


class SnapshotUnavailable(Exception):
    """The road's snapshot cannot be used this session; `reason` closes the road."""

    def __init__(self, reason: ClosureReason, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else str(reason))
        self.reason = reason


@runtime_checkable
class SnapshotSource(Protocol):
    def for_road(self, road_day: RoadDay) -> SlotSnapshot:
        """The road's verified snapshot, or `SnapshotUnavailable` with its closure reason."""
