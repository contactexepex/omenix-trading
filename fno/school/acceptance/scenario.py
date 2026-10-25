"""One recorded session as plain data (story MS-P1i): what each road's capture holds, what the archived NSE listing and
the dated lot copy say about it, the drivers' scripted proposals and the timing of the seal. The harness feeds it to a
fleet (the fake rig here, the real wiring in MS-P1j) and a fault planter returns a changed copy.

The data is what the real detectors read, never a verdict: part b's catalogue compares `snapshots[road].expiries` with
`listed_expiries[road]` and the lot of each expiry in `lots[road]`, and its quality gate reads the quotes. Data only: no
port, no clock, no production path."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from ..constants import RoadCode
from ..contracts.decisions import DriverCard, Proposal
from ..contracts.snapshot import ContractKey, SlotQuote, SlotSnapshot


@dataclass(frozen=True)
class DriverPlan:
    """A driver that proposes `proposal` on every open road (no trade when None)."""

    card: DriverCard
    proposal: Proposal | None = None


@dataclass(frozen=True)
class Scenario:
    session: date
    snapshots: Mapping[RoadCode, SlotSnapshot]  # the quotes, expiries and times each road's capture holds
    listed_expiries: Mapping[RoadCode, tuple[date, ...]]  # what the archived NSE listing says the road records
    lots: Mapping[RoadCode, Mapping[date, int]]  # the session's dated lot copy: units per expiry
    drivers: tuple[DriverPlan, ...]
    cap_rs: float  # the per-trade maximum loss the laws enforce
    fill_at: datetime  # when the fleet fills
    seal_pushed_at: datetime  # when the decisions file's receipt reaches the remote

    @property
    def roads(self) -> tuple[RoadCode, ...]:
        return tuple(self.snapshots)

    @property
    def scheduled(self) -> set[tuple[RoadCode, str]]:
        """Every scheduled road decision: (road, driver id), one per recorded road of each driver version's card (its
        `roads`, CARD_P1 section 1), as the fleet schedules them."""
        return {
            (road, plan.card.driver_id) for plan in self.drivers for road in self.snapshots if road in plan.card.roads
        }

    def with_snapshot(self, road: RoadCode, snapshot: SlotSnapshot) -> "Scenario":
        return replace(self, snapshots={**self.snapshots, road: snapshot})

    def with_expiries_shifted(self, road: RoadCode, days: int) -> "Scenario":
        """The capture's contracts carry expiries `days` later than the listing's: every key, and the expiry list."""
        snapshot = self.snapshots[road]
        shift = timedelta(days=days)
        quotes = {replace(key, expiry=key.expiry + shift): quote for key, quote in snapshot.quotes.items()}
        return self.with_snapshot(road, replace(snapshot, quotes=quotes,
                                                expiries=tuple(e + shift for e in snapshot.expiries)))  # fmt: skip

    def with_lot(self, road: RoadCode, expiry: date, units: int) -> "Scenario":
        return replace(self, lots={**self.lots, road: {**self.lots[road], expiry: units}})

    def with_quote(self, road: RoadCode, key: ContractKey, quote: SlotQuote) -> "Scenario":
        snapshot = self.snapshots[road]
        return self.with_snapshot(road, replace(snapshot, quotes={**snapshot.quotes, key: quote}))

    def without_quote(self, road: RoadCode, key: ContractKey) -> "Scenario":
        snapshot = self.snapshots[road]
        return self.with_snapshot(
            road, replace(snapshot, quotes={k: q for k, q in snapshot.quotes.items() if k != key})
        )

    def with_plan(self, plan: DriverPlan) -> "Scenario":
        """Adds a driver, or replaces the one with the same driver id."""
        kept = tuple(p for p in self.drivers if p.card.driver_id != plan.card.driver_id)
        return replace(self, drivers=(*kept, plan))
