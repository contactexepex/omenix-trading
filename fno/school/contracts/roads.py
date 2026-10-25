"""Roads (story 3.1): where a decision can happen. Five fixed roads, each one capture dataset at the 15:00 slot."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable

from ..constants import MONTHLY_DATASET, WEEKLY_DATASET, ClosureReason, ExpiryKind, RoadCode


@dataclass(frozen=True)
class Road:
    code: RoadCode
    underlying: str
    expiry_kind: ExpiryKind
    dataset: str  # the quote store's dataset (`MONTHLY_DATASET` or `WEEKLY_DATASET`)
    stem: str  # the capture file stem (`<stem>_<YYYYMMDD>.canonical`)


ROADS = (
    Road(RoadCode.NIFTY_MONTHLY, "NIFTY", ExpiryKind.MONTHLY, MONTHLY_DATASET, "nifty"),
    Road(RoadCode.BANKNIFTY_MONTHLY, "BANKNIFTY", ExpiryKind.MONTHLY, MONTHLY_DATASET, "banknifty"),
    Road(RoadCode.FINNIFTY_MONTHLY, "FINNIFTY", ExpiryKind.MONTHLY, MONTHLY_DATASET, "finnifty"),
    Road(RoadCode.MIDCPNIFTY_MONTHLY, "MIDCPNIFTY", ExpiryKind.MONTHLY, MONTHLY_DATASET, "midcpnifty"),
    Road(RoadCode.NIFTY_WEEKLY, "NIFTY", ExpiryKind.WEEKLY, WEEKLY_DATASET, "niftyweekly"),
)
ROADS_BY_CODE = {road.code: road for road in ROADS}


@dataclass(frozen=True)
class DatedLot:
    units: int  # contract multiplier in force that session
    source: str  # where it was read (e.g. the A20a master file's path), so a mismatch can be named


@dataclass(frozen=True)
class RoadStatus:
    """Open, or closed with exactly one reason and, if known, a plain detail (e.g. why a listing was unreadable).
    The fleet records the detail in the decision record's `inputs` under `ROAD_DETAIL_INPUT`."""

    closed_by: ClosureReason | None = None
    detail: str = ""

    def __post_init__(self):
        if self.detail and self.closed_by is None:
            raise ValueError("only a closed road carries a detail")

    @property
    def open(self) -> bool:
        return self.closed_by is None


OPEN = RoadStatus()


@dataclass(frozen=True)
class RoadDay:
    road: Road
    session: date
    expiries: tuple[date, ...]  # the expiries the road's capture records that session, nearest first
    lot: DatedLot | None
    strike_step: float | None  # the nearest expiry's step
    status: RoadStatus
    # Each recorded expiry's own step (MS-P1a2: FINNIFTY's November monthly lists 100-point strikes, October 50).
    strike_steps: Mapping[date, float] = field(default_factory=dict, hash=False)
    # Each recorded expiry's own dated lot (MS-P1a4): NSE changes a lot from a given expiry, so for a while an index's
    # two monthlies can carry different lots. `lot` stays the nearest expiry's. Left out, every recorded expiry
    # carries `lot`: what a catalogue that closes a road on mixed lots states (every one today).
    lots: Mapping[date, DatedLot] = field(default_factory=dict, hash=False)

    def __post_init__(self):
        if self.status.open and (self.lot is None or self.strike_step is None or not self.expiries):
            raise ValueError("an open road needs its expiries, dated lot and strike step")
        if tuple(sorted(self.expiries)) != self.expiries:
            raise ValueError("expiries must be nearest first")
        if self.strike_steps:
            if set(self.strike_steps) != set(self.expiries) or min(self.strike_steps.values()) <= 0:
                raise ValueError("strike steps name every recorded expiry, each above zero")
            if self.strike_steps[self.expiries[0]] != self.strike_step:
                raise ValueError("the nearest expiry's step is `strike_step`")
        if self.lots:
            if set(self.lots) != set(self.expiries) or min(lot.units for lot in self.lots.values()) <= 0:
                raise ValueError("lots name every recorded expiry, each above zero")
            if self.lots[self.expiries[0]] != self.lot:
                raise ValueError("the nearest expiry's lot is `lot`")

    def step_for(self, expiry: date) -> float:
        """That expiry's own strike step; never another expiry's (a driver stepping out on a later expiry)."""
        if expiry in self.strike_steps:
            return self.strike_steps[expiry]
        if self.expiries and expiry == self.expiries[0] and self.strike_step:
            return self.strike_step
        raise ValueError(f"no strike step recorded for {expiry}")

    def lot_for(self, expiry: date) -> DatedLot:
        """That expiry's own lot; never another expiry's (a lot changed from a later expiry). Without `lots`, every
        recorded expiry carries `lot`; an expiry the road did not record has none."""
        if self.lots:
            if expiry not in self.lots:
                raise ValueError(f"no lot recorded for {expiry}")
            return self.lots[expiry]
        if expiry not in self.expiries or self.lot is None:
            raise ValueError(f"no lot recorded for {expiry}")
        return self.lot


@runtime_checkable
class RoadCatalogue(Protocol):
    def day(self, session: date) -> tuple[RoadDay, ...]:
        """Every road of a trading session (closed ones with their reason); none on a non-trading day."""
