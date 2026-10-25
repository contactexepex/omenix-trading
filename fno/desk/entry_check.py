"""The entry check (story E4c, decisions 30 and 43): before any leg fills, at the execution snapshot, every leg's
opening side must fill and every protective (bought) leg must also be sellable back there. On paper every quote of the
snapshot is known before the first fill, so a trade that would be unwound, or closed at once because its protection
cannot be sold, is refused before anything is bought (design 3.2: all legs fill at one snapshot or none).

Story E4d: a book's entries at one snapshot share its displayed size. The units the book has already taken there, per
contract and touch side, are added to this entry's units, so a later entry that no longer fits is refused rather than
over-filled. Each book counts only its own records (E1's firewall).

It prices with E4's `price_leg`, so it adds no second pricing rule, and depends only on the snapshot and the records it
is given, so E8 can apply it at each of its snapshots. A problem names the contract and the units, never a quote
figure (E2b)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from ..constants import (
    FILL_OPEN,
    PROTECTION_NOT_BUYABLE,
    PROTECTION_NOT_SELLABLE,
    SHORT_LEG_NOT_SELLABLE,
    SIDE_SELL,
    SIZE_SHARED_IN_BOOK,
)
from ..research_engine.structures import BOUGHT
from .pricing import DeskLeg, price_leg
from .records import OPENING_SIDE
from .snapshot import ExecutionSnapshot

PROBLEM = "{code} ({contract}, {units} units)"
SHARED = "{code} ({contract}, {units} units, {taken} already taken in this book at this snapshot)"

Taken = Mapping[tuple[str, str], int]


def taken_units(fill_rows: Iterable[Mapping[str, str]], snapshot: ExecutionSnapshot, trade_id: str) -> Taken:
    """(contract, side) -> the units the book's other trades took at this snapshot: every fill row there by its side
    (a buy takes ask size, a sell bid size), plus each protective leg's sell-back need still held (its bought units less
    those already sold back there), on the bid side as E4c checks it. The trade being checked never counts itself."""
    rows = [r for r in fill_rows if _at(r, snapshot) and r["trade_id"] != trade_id]
    taken: Counter[tuple[str, str]] = Counter()
    held: Counter[tuple[str, str]] = Counter()  # (trade, contract) -> protective units bought less sold back
    for row in rows:
        taken[(row["contract"], row["side"])] += int(row["units"])
        if row["opening_side"] == OPENING_SIDE[BOUGHT]:
            held[(row["trade_id"], row["contract"])] += int(row["units"]) * (1 if row["action"] == FILL_OPEN else -1)
    for (_, contract), units in held.items():
        taken[(contract, SIDE_SELL)] += max(units, 0)
    return dict(taken)


def _at(row: Mapping[str, str], snapshot: ExecutionSnapshot) -> bool:
    return row["snapshot_id"] == snapshot.snapshot_id and row["snapshot_sha256"] == snapshot.sha256


def entry_problems(
    snapshot: ExecutionSnapshot, legs: Sequence[DeskLeg], units: int, taken: Taken | None = None
) -> list[str]:
    """Every failing check, in the fixed order: the legs as given (E4's order, protection first), for each its opening
    side, then a protective leg's closing side. A side failing on its own records E4c's code; one failing only with
    the units already `taken` records `size_shared_in_book`. Empty when the entry may fill."""
    problems = []
    for leg in legs:
        problem = _side_problem(snapshot, leg, True, units, taken or {})
        if not problem and leg.protective:
            problem = _side_problem(snapshot, leg, False, units, taken or {})
        if problem:
            problems.append(problem)
    return problems


def _side_problem(snapshot: ExecutionSnapshot, leg: DeskLeg, opening: bool, units: int, taken: Taken) -> str:
    side = leg.side(opening)
    if not price_leg(snapshot, leg, side, units).fills:
        return PROBLEM.format(code=_code(leg, opening), contract=leg.contract, units=units)
    already = taken.get((leg.contract, side), 0)
    if already and not price_leg(snapshot, leg, side, units + already).fills:
        return SHARED.format(code=SIZE_SHARED_IN_BOOK, contract=leg.contract, units=units, taken=already)
    return ""


def _code(leg: DeskLeg, opening: bool) -> str:
    if not opening:
        return PROTECTION_NOT_SELLABLE
    return PROTECTION_NOT_BUYABLE if leg.protective else SHORT_LEG_NOT_SELLABLE
