"""Each open school position valued at this slot (story MS-P1d): its cash flow so far (E1's ledger) plus every held
leg at the mid of its road's valid two-sided quote, which is E2d's `open_trades_value` identity. A position with any
leg its road's snapshot cannot mark counts at its worst case, minus its maximum loss, and its contracts are reported
as unmarked (stale): no price is taken from another snapshot or invented (story 3.1). The worst case keeps the daily
stop safe; the brake never engages on such a session (`brake.py`)."""

from collections.abc import Mapping
from dataclasses import dataclass

from ..constants import SIDE_BUY, RoadCode
from ..contracts.decisions import OpenPosition
from ..contracts.roads import ROADS_BY_CODE
from ..contracts.snapshot import SlotSnapshot
from ..execution.desk_view import contract_symbol


@dataclass(frozen=True)
class Valuation:
    open_value: float  # the open positions' cash flow so far plus their legs at this slot's mids
    unmarked: tuple[str, ...]  # contracts with no usable mark, each position counted at its worst case


def value_positions(positions: list[OpenPosition], cash_flows: Mapping[str, float],
                    marks: Mapping[RoadCode, SlotSnapshot]) -> Valuation:  # fmt: skip
    total, unmarked = 0.0, []
    for position in positions:
        legs_value, missing = _legs_value(position, marks.get(position.road))
        if missing:
            total -= position.max_loss
            unmarked += missing
        else:
            total += cash_flows[position.position_id] + legs_value
    return Valuation(total, tuple(sorted(set(unmarked))))


def _legs_value(position: OpenPosition, snapshot: SlotSnapshot | None) -> tuple[float, list[str]]:
    underlying = ROADS_BY_CODE[position.road].underlying
    value, missing = 0.0, []
    for leg in position.legs:
        quote = None if snapshot is None else snapshot.quote(leg.key)
        mid = None if quote is None else quote.mid
        if mid is None:
            missing.append(contract_symbol(underlying, leg.key))
            continue
        value += (1 if leg.side == SIDE_BUY else -1) * leg.lots * position.lot * mid
    return value, missing
