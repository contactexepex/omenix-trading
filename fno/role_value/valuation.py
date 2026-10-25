"""Both decisions of a pair valued as scoreboard A values a book's action (story F9a; S1 `role_value_schedule`: "valued
like scoreboard A"): every opportunity of E2's common set read by S3's `action_of`, each take valued by S3's standard
unit (one lot, E4 fills at the day's execution snapshot, C1 charges, time exit, E7 settlement), imported, never
copied. A skip (a no-trade or a rejected trade) and a take that does not fill are 0. A pair with an action still open
waits; one with an opportunity not observed or a maximum loss that cannot be computed is not scored (S3's reasons)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..scoreboard.matched import unit_legs
from ..scoreboard.matched_actions import NOT_OBSERVED, TAKE, action_of
from ..scoreboard.matched_days import NO_RECORD, OTHER_PACK, CommonSet
from ..scoreboard.standard_unit import CLOSED, NOT_FILLED, OPEN, StandardUnit

SCORED, WAITING, NOT_SCORED = "scored", "open", "not scored"
NO_COMMON_PACK, NO_DECISION = "no common pack for the day", "{side} decision not found"


@dataclass(frozen=True)
class SideValue:
    status: str
    net: float = 0.0
    max_loss: float = 0.0
    choices: tuple = ()  # what was decided on each opportunity: the take's legs, or a skip
    note: str = ""


@dataclass(frozen=True)
class PairValue:
    status: str
    difference: float = 0.0  # with the unit minus without it, rupees
    changed: bool = False
    max_loss_difference: float = 0.0
    note: str = ""


def _choice(opportunity_id: str, kind: str, record: Mapping | None) -> tuple:
    if kind != TAKE:
        return (opportunity_id, kind)
    legs = tuple((leg["contract"], float(leg["strike"]), leg["type"], int(leg["side"]))
                 for leg in record["structure"]["legs"])  # fmt: skip
    return (opportunity_id, kind, legs)


def value_side(records: Sequence[Mapping], common: CommonSet, day: date, unit: StandardUnit, on: date) -> SideValue:
    by_id = {r["opportunity_id"]: r for r in records}
    net = max_loss = 0.0
    choices, waiting = [], False
    for entry in common.opportunities:
        record = by_id.get(entry["opportunity_id"])
        if record is None or record.get("common_pack_sha256") != common.sha256:
            return SideValue(NOT_SCORED, note=f"{entry['opportunity_id']}: {OTHER_PACK if record else NO_RECORD}")
        action = action_of(record)
        if action.kind == NOT_OBSERVED:
            return SideValue(NOT_SCORED, note=f"{entry['opportunity_id']}: {action.reason}")
        choices.append(_choice(entry["opportunity_id"], action.kind, record))
        if action.kind != TAKE:
            continue
        legs = unit_legs(record, date.fromisoformat(entry["expiry"]))
        result = unit.value(legs, day, date.fromisoformat(entry["exit_day"]), on)
        if result.status == OPEN:
            waiting = True
        elif result.status == CLOSED:
            net, max_loss = net + result.net, max_loss + result.max_loss
        elif result.status != NOT_FILLED:
            return SideValue(NOT_SCORED, note=f"{entry['opportunity_id']}: {result.status}")
    return SideValue(WAITING if waiting else SCORED, net, max_loss, tuple(choices))


def value_pair(real: Sequence[Mapping] | None, shadow: Sequence[Mapping] | None, common: CommonSet | None,
               day: date, unit: StandardUnit, on: date) -> PairValue:  # fmt: skip
    if common is None:
        return PairValue(NOT_SCORED, note=NO_COMMON_PACK)
    for side, records in (("real", real), ("shadow", shadow)):
        if records is None:
            return PairValue(NOT_SCORED, note=NO_DECISION.format(side=side))
    with_unit, without = value_side(real, common, day, unit, on), value_side(shadow, common, day, unit, on)
    for status in (NOT_SCORED, WAITING):  # a side that can never be scored outranks one that is only waiting
        for side, value in (("real", with_unit), ("shadow", without)):
            if value.status == status:
                return PairValue(status, note=f"{side}: {value.note or 'an action still open'}")
    return PairValue(
        SCORED, round(with_unit.net - without.net, 2), with_unit.choices != without.choices,
        round(with_unit.max_loss - without.max_loss, 2),
    )  # fmt: skip
