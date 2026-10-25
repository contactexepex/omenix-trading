"""The planted faults of story MS-P1i: each changes a scenario and says what must come out. A fleet that catches the
fault gives exactly the named reason code and opens no position for it (the harness checks both). Planters are pure
edits of a `Scenario`; none touches a store or a clock, and none has a production path."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import timedelta
from enum import StrEnum

from ...constants import SIDE_SELL
from ..constants import ClosureReason, DriverRole, OptionKind, RefusalReason, RoadCode
from ..contracts.decisions import DriverCard, LegSpec, Proposal
from ..contracts.snapshot import ContractKey
from .scenario import DriverPlan, Scenario


class Expect(StrEnum):
    ROAD_CLOSED = "road_closed"  # every driver's decision on the road is road_closed with `reason`
    REFUSED_OR_UNFILLED = "refused_or_unfilled"  # the entry is refused with `reason` (by a law or at the fill)
    ALL_FILLS_STALE = "all_fills_stale"  # every fill of the session is refused stale_seal
    REPLAY_CONFLICT = "replay_conflict"  # other bytes for the sealed key raise ReplayConflict and change nothing


@dataclass(frozen=True)
class Fault:
    name: str
    plant: Callable[[Scenario], Scenario]
    expect: Expect
    reason: str  # the exact reason code expected ("" where the expectation is an exception)
    road: RoadCode | None = None
    driver_id: str | None = None


def _first_trader(scenario: Scenario) -> DriverPlan:
    return next(p for p in scenario.drivers if p.proposal is not None)


def _sold_leg(proposal: Proposal) -> LegSpec:
    return next(leg for leg in proposal.legs if leg.side == SIDE_SELL)


def missing_quote(road: RoadCode) -> Fault:
    """The quote of the trading driver's short leg is not in the road's snapshot."""

    def plant(scenario: Scenario) -> Scenario:
        return scenario.without_quote(road, _sold_leg(_first_trader(scenario).proposal).key)

    return Fault("missing quote", plant, Expect.REFUSED_OR_UNFILLED, RefusalReason.MISSING_QUOTE, road, None)


def expiry_mismatch(road: RoadCode, days: int = 7) -> Fault:
    """The capture's contracts carry expiries a week later than the archived listing says the road records."""
    return Fault("expiry mismatch", lambda s: s.with_expiries_shifted(road, days), Expect.ROAD_CLOSED,
                 ClosureReason.EXPIRY_MISMATCH, road)  # fmt: skip


def lot_mismatch(road: RoadCode, units: int = 35) -> Fault:
    """The dated lot copy gives the road's later expiry another lot than its earlier one: no single lot."""

    def plant(scenario: Scenario) -> Scenario:
        later = scenario.snapshots[road].expiries[-1]
        return scenario.with_lot(road, later, units)

    return Fault("lot mismatch", plant, Expect.ROAD_CLOSED, ClosureReason.LOT_MISMATCH, road)


def impossible_price(road: RoadCode) -> Fault:
    """Two strikes of one expiry and type quoted so that no prices inside their bid-ask ranges fit a vertical worth
    0 to its width (`quality.prices.impossible_keys`): the dearer leg's whole range sits below the cheaper leg's bid."""

    def plant(scenario: Scenario) -> Scenario:
        snapshot = scenario.snapshots[road]
        expiry = snapshot.expiries[0]
        kind = next(k.kind for k in snapshot.quotes if k.expiry == expiry)
        strikes = sorted(k.strike for k in snapshot.quotes if k.expiry == expiry and k.kind is kind)
        low, high = (ContractKey(expiry, strike, kind) for strike in strikes[:2])
        dearer, cheaper = (
            (low, high) if kind is OptionKind.CALL else (high, low)
        )  # calls fall with the strike, puts rise
        floor = snapshot.quotes[cheaper].bid
        broken = replace(snapshot.quotes[dearer], bid=floor / 4, ask=floor / 2)
        return scenario.with_quote(road, dearer, broken)

    return Fault("impossible price", plant, Expect.ROAD_CLOSED, ClosureReason.IMPOSSIBLE_PRICE, road)


def stale_seal() -> Fault:
    """The decisions file's receipt reaches the remote one second after the fills."""
    return Fault("stale seal", lambda s: replace(s, seal_pushed_at=s.fill_at + timedelta(seconds=1)),
                 Expect.ALL_FILLS_STALE, RefusalReason.STALE_SEAL)  # fmt: skip


def replay_conflict() -> Fault:
    return Fault("replay conflict", lambda s: s, Expect.REPLAY_CONFLICT, "")


def refused_entry(road: RoadCode, code: str = "OVR", version: str = "1", cap_multiple: float = 1.2) -> Fault:
    """A planted driver whose trade has a maximum loss above the per-trade cap, so the law refuses it."""
    card = DriverCard(code, version, "planted", DriverRole.RULE, (road,), 1)

    def plant(scenario: Scenario) -> Scenario:
        template = _first_trader(scenario).proposal
        over = replace(template, max_loss=scenario.cap_rs * cap_multiple, costs=min(template.costs, scenario.cap_rs))
        return scenario.with_plan(DriverPlan(card, over))

    return Fault("planted refused entry", plant, Expect.REFUSED_OR_UNFILLED, RefusalReason.MAX_LOSS, road,
                 card.driver_id)  # fmt: skip


def all_faults(road: RoadCode = RoadCode.BANKNIFTY_MONTHLY) -> tuple[Fault, ...]:
    return (missing_quote(road), expiry_mismatch(road), lot_mismatch(road), stale_seal(), impossible_price(road),
            replay_conflict(), refused_entry(road))  # fmt: skip
