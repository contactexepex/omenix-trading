"""A `LedgerEntry` as E1's fills (story MS-P1d): each filled leg becomes one `Fill` with C1's charges on its price
(a settlement charged as one, story E7), its ID `<position>:<open|close|settle>:<contract>`, so a retried entry is
E1's no-op. The entry must match its position exactly, or nothing is written:
- an opening fills every leg of the position, on its side, for lots x lot units;
- a closing fills every leg on the opposite side for the same units, so the trade ends flat;
- each leg's charges equal C1's charges on that fill (the fill port and the account price one way)."""

from collections import Counter
from collections.abc import Mapping

from ...accounting.ledgers import Order
from ...books.fills import Fill
from ...constants import FILL_CLOSE, FILL_OPEN, FILL_SETTLE
from ..constants import ExitReason
from ..contracts.accounts import FilledLeg, LedgerEntry
from ..contracts.roads import ROADS_BY_CODE
from ..execution.desk_view import contract_symbol
from ..execution.settlement_fills import CLOSING_SIDE, settled_order

CHARGES_TOLERANCE_RS = 1e-6


class EntryMismatch(ValueError):
    """The fill does not open or close its position exactly: nothing is recorded."""


def ledger_fills(entry: LedgerEntry, charges: Mapping[str, float]) -> list[Fill]:
    position = entry.position
    if len({leg.key for leg in position.legs}) != len(position.legs):
        raise EntryMismatch(f"{position.position_id}: a position names a contract twice (one fill ID per contract)")
    settling = entry.exit_reason == ExitReason.EXPIRY
    expected = Counter((leg.key, CLOSING_SIDE[leg.side] if entry.closes else leg.side, leg.lots * position.lot)
                       for leg in position.legs)  # fmt: skip
    if Counter((leg.key, leg.side, leg.units) for leg in entry.fill.legs) != expected:
        raise EntryMismatch(f"{position.position_id}: the {_action(entry)} fill does not match the position's legs")
    underlying = ROADS_BY_CODE[position.road].underlying
    return [_fill(entry, leg, underlying, settling, charges) for leg in entry.fill.legs]


def _fill(entry: LedgerEntry, leg: FilledLeg, underlying: str, settling: bool, charges: Mapping[str, float]) -> Fill:
    contract = contract_symbol(underlying, leg.key)
    order = settled_order(leg.side, leg.price, leg.units) if settling else Order(leg.side, leg.price, leg.units, 0.0)
    position_id = entry.position.position_id
    fill = Fill.priced(f"{position_id}:{_action(entry)}:{contract}", position_id, entry.fill.filled_at, contract, order,
                       dict(charges))  # fmt: skip
    if abs(sum(fill.charges.values()) - leg.charges) > CHARGES_TOLERANCE_RS:
        raise EntryMismatch(f"{position_id}: {contract}'s charges differ from C1's on its fill")
    return fill


def _action(entry: LedgerEntry) -> str:
    if not entry.closes:
        return FILL_OPEN
    return FILL_SETTLE if entry.exit_reason == ExitReason.EXPIRY else FILL_CLOSE
