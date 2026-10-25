"""Checks and records every driver shares (story MS-P1e): a driver is only asked about its own roads on an open road
with that road's own snapshot, and every no-trade carries a reason from a's enum."""

from ..constants import NoTradeReason, Outcome
from ..contracts.decisions import Decision, DriverCard, OpenPosition, Proposal
from ..contracts.roads import RoadDay
from ..contracts.snapshot import SlotSnapshot


class OutOfScope(ValueError):
    """A driver was asked about a road, day or snapshot it does not decide on: a caller bug, never a no-trade."""


def check_scope(card: DriverCard, road_day: RoadDay, snapshot: SlotSnapshot) -> None:
    if road_day.road.code not in card.roads:
        raise OutOfScope(f"{card.driver_id} does not drive {road_day.road.code}")
    if not road_day.status.open:
        raise OutOfScope(f"{road_day.road.code} is closed on {road_day.session}: a closed road gets no driver call")
    if (snapshot.road, snapshot.session) != (road_day.road.code, road_day.session):
        raise OutOfScope(f"snapshot {snapshot.road} {snapshot.session} is not {road_day.road.code} {road_day.session}")


def no_trade(card: DriverCard, road_day: RoadDay, reason: NoTradeReason) -> Decision:
    return Decision(card.driver_id, road_day.road.code, road_day.session, Outcome.NO_TRADE, reason)


def trade(card: DriverCard, road_day: RoadDay, proposal: Proposal) -> Decision:
    return Decision(card.driver_id, road_day.road.code, road_day.session, Outcome.TRADE, "", proposal)


def own_positions(card: DriverCard, road_day: RoadDay, positions: tuple[OpenPosition, ...]) -> tuple[OpenPosition, ...]:
    return tuple(p for p in positions if p.driver_id == card.driver_id and p.road == road_day.road.code)
