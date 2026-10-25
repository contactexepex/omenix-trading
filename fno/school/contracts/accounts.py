"""Accounts and fills (stories 3.3, 3.6): one paper account per driver version; fills at the decision snapshot's
touch after the seal, never partial and never invented; expiry legs settled at intrinsic from the settlement file."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from ..constants import SIDE_SELL, SIDES, ExitReason, ExitState, RefusalReason, RoadCode
from .decisions import Decision, OpenPosition
from .safety import AccountView
from .seal import Seal
from .snapshot import ContractKey, SlotSnapshot


@dataclass(frozen=True)
class FilledLeg:
    key: ContractKey
    side: str
    units: int
    price: float  # the touch (ask to buy, bid to sell), or the intrinsic value at settlement
    charges: float  # C1's charges on this fill

    def __post_init__(self):
        if self.side not in SIDES or self.units < 1 or self.price < 0 or self.charges < 0:
            raise ValueError("a filled leg needs a side, units, and no negative price or charge")


@dataclass(frozen=True)
class FillResult:
    """Every leg filled, or none with the reasons, or a position that could not close with its state."""

    legs: tuple[FilledLeg, ...] = ()
    refused: tuple[RefusalReason, ...] = ()
    state: ExitState | None = None
    filled_at: datetime | None = None
    rests_on: str = ""  # SHA-256 of the sealed decision file, or of NSE's settlement file for a settlement

    def __post_init__(self):
        if sum((bool(self.legs), bool(self.refused), self.state is not None)) != 1:
            raise ValueError("a fill result is exactly one of: filled legs, a refusal, a state")
        if self.legs and (self.filled_at is None or self.filled_at.tzinfo is None or not self.rests_on):
            raise ValueError("filled legs carry their aware time and the file they rest on")

    @property
    def filled(self) -> bool:
        return bool(self.legs)

    @property
    def cash(self) -> float:
        """Rupees the fill moves: premium (or settlement value) received minus paid, less every charge."""
        return sum((leg.price if leg.side == SIDE_SELL else -leg.price) * leg.units - leg.charges for leg in self.legs)


@dataclass(frozen=True)
class LedgerEntry:
    """What an account records: a position opened by an entry fill, or closed by an exit or settlement fill."""

    position: OpenPosition
    fill: FillResult
    closes: bool
    exit_reason: ExitReason | None = None
    # The session whose run recorded it (MS-P1j; orchestrator's ruling b, 22 Oct 2026): a session date, not a clock
    # time, so a replay stays byte-identical; a rerun rebuilds that session's settlements from it. The fleet always
    # sets it; None only for entries made outside a session's run.
    recorded_for: date | None = None

    def __post_init__(self):
        if not self.fill.filled:
            raise ValueError("an account records filled results only")
        if self.closes != (self.exit_reason is not None):
            raise ValueError("a close names its exit reason; an entry names none")


@dataclass(frozen=True)
class SealedDecision:
    """A decision with the SHA-256 of the dashcam file that holds it, as its seal must name."""

    decision: Decision
    file_sha256: str


@dataclass(frozen=True)
class SettlementPrice:
    price: float  # the index's final settlement price
    file_sha256: str  # of the archived settlement file it was read from


class SettlementUnavailable(Exception):
    """No settlement file for that expiry yet, or no single clear price in it: the position stays
    `settlement_needed`."""


@runtime_checkable
class IndexSettlementSource(Protocol):
    def price(self, underlying: str, expiry: date) -> SettlementPrice: ...


@runtime_checkable
class AccountPort(Protocol):
    def view(self, driver_id: str, marks: Mapping[RoadCode, SlotSnapshot], session: date) -> AccountView:
        """The driver's account at this slot, every open position marked on its road's snapshot; opened at the
        school's `account_rs` on first use."""

    def record(self, driver_id: str, entry: LedgerEntry) -> None:
        """Append one entry to the driver's append-only ledger; the same entry again is a no-op. An account no `view`
        has opened refuses it (d's store raises `AccountError`): whoever records, views first (MS-P1j)."""


@runtime_checkable
class LedgerReader(Protocol):
    def entries(self, driver_id: str) -> tuple[LedgerEntry, ...]:
        """Every entry recorded in the driver's account, in the order recorded: each opening, then its closing (with
        its ExitReason) once closed. Read-only: it opens no account and writes no equity row. An account never opened
        gives ()."""


@runtime_checkable
class FillPort(Protocol):
    def enter(self, sealed: SealedDecision, snapshot: SlotSnapshot, seal: Seal, at: datetime) -> FillResult:
        """Refuses `stale_seal` unless `seal.covers(sealed.file_sha256, at)`; else every leg at the touch or none."""

    def exit(self, position: OpenPosition, snapshot: SlotSnapshot, file_sha256: str, seal: Seal,
             at: datetime) -> FillResult:  # fmt: skip
        """Closes at the touch, short legs first; a missing quote gives `exit_waiting_quote`, never a guessed price."""

    def settle(self, position: OpenPosition, expiry: date) -> FillResult:
        """Expired legs at intrinsic against `IndexSettlementSource`; `settlement_needed` until its file exists."""
