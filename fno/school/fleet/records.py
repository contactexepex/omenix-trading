"""The decision records the fleet seals (story 3.4), one per scheduled (road, driver version), and the exit records of
the positions a card closes at this slot."""

from ..constants import ROAD_DETAIL_INPUT, SLOT_1500, Outcome, UnavailableReason
from ..contracts.decisions import Decision, DriverCard
from ..contracts.records import DecisionRecord, WitnessedQuote
from ..contracts.roads import RoadDay
from ..contracts.safety import LawResult
from ..contracts.snapshot import SlotSnapshot
from .slot import ClosedRoad

HISTORY_INPUT = "history_sessions"
ERROR_INPUT = "driver_error_class"  # the exception's class name only, never its message


def closed_record(card: DriverCard, road: ClosedRoad) -> DecisionRecord:
    day = road.road_day
    decision = Decision(card.driver_id, day.road.code, day.session, Outcome.ROAD_CLOSED, road.reason)
    inputs = {ROAD_DETAIL_INPUT: road.detail} if road.detail else {}
    return DecisionRecord(day.session, SLOT_1500, day.road.code, card.card_sha256, "", "", road.reason, decision,
                          inputs=inputs)  # fmt: skip


def decision_record(card: DriverCard, decision: Decision, snapshot: SlotSnapshot, laws: tuple[LawResult, ...],
                    history_sessions: int, error_class: str = "") -> DecisionRecord:  # fmt: skip
    legs = decision.proposal.legs if decision.proposal else ()
    witnessed = tuple(WitnessedQuote(leg.key, snapshot.quote(leg.key)) for leg in legs if snapshot.quote(leg.key))
    inputs: dict = {HISTORY_INPUT: history_sessions}
    if error_class:
        inputs[ERROR_INPUT] = error_class
    return DecisionRecord(decision.session, SLOT_1500, decision.road, card.card_sha256, snapshot.snapshot_id,
                          snapshot.sha256, None, decision, laws, witnessed, inputs)  # fmt: skip


def unavailable(card: DriverCard, road_day: RoadDay, reason: UnavailableReason) -> Decision:
    return Decision(card.driver_id, road_day.road.code, road_day.session, Outcome.UNAVAILABLE, reason)
