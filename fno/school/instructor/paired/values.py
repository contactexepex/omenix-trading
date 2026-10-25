"""The value of one driver's decision on one road-slot (story MS-INS, part d): a closed entry's return on risk, an
abstention's 0 (kept and counted), or no value yet (open) or at all (unavailable, road closed, entry never filled)."""

import math
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ...constants import Outcome, RoadCode
from ...contracts.records import DecisionRecord, OutcomeRecord

SlotKey = tuple[str, RoadCode, date]  # (driver ID, road, session of the entry decision)


class SlotStatus(StrEnum):
    CLOSED = "closed"
    ABSTAINED = "abstained"  # no trade, or refused: worth 0 and counted
    OPEN = "open"
    UNAVAILABLE = "unavailable"  # unavailable, road closed, or a fired entry that never filled: left out and counted


@dataclass(frozen=True)
class RoadSlot:
    session: date
    road: RoadCode
    driver_id: str
    status: SlotStatus
    return_on_risk: float | None = None
    is_ticket: bool = False

    def __post_init__(self):
        if (self.status == SlotStatus.CLOSED) != (self.return_on_risk is not None):
            raise ValueError("a return on risk exactly for a closed entry")
        if self.return_on_risk is not None and not math.isfinite(self.return_on_risk):
            raise ValueError("a return on risk is a finite number")


def road_slot(
    record: DecisionRecord, closed: Mapping[SlotKey, OutcomeRecord], unfilled: Collection[SlotKey]
) -> RoadSlot:
    """`closed` holds each entry's latest outcome by its slot; `unfilled` the fired entries that never filled (the
    displayed size shared out, or a refused fill)."""
    decision = record.decision
    key: SlotKey = (decision.driver_id, record.road, record.session)
    slot = RoadSlot(record.session, record.road, decision.driver_id, SlotStatus.UNAVAILABLE)
    if decision.outcome in (Outcome.NO_TRADE, Outcome.REFUSED):
        return RoadSlot(record.session, record.road, decision.driver_id, SlotStatus.ABSTAINED)
    if decision.outcome not in (Outcome.TRADE, Outcome.TICKET) or key in unfilled:
        return slot
    outcome = closed.get(key)
    if outcome is None:  # a ticket stays a ticket while open: executed-only already values it at 0
        return RoadSlot(record.session, record.road, decision.driver_id, SlotStatus.OPEN, None,
                        decision.outcome == Outcome.TICKET)  # fmt: skip
    return RoadSlot(record.session, record.road, decision.driver_id, SlotStatus.CLOSED, outcome.return_on_risk,
                    outcome.is_ticket)  # fmt: skip
