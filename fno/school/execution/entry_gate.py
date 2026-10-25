"""The entry quote gate (story 3.3, law 5) on E4's rules: every leg's opening side at a valid two-sided A4 quote whose
displayed size covers its units, and every protective leg sellable back there (E4c), counting the units the same
account already took at this snapshot (E4d, per account: each driver version is its own account, story 3.6 and
response 327 item 10). E4c/E4d's `entry_problems` is the authority on whether the entry may fill; each failing side is
then named by one school refusal reason, from E4's own `price_leg` answer, never from its text."""

from collections import Counter
from collections.abc import Iterable, Mapping

from ...desk.entry_check import entry_problems
from ...desk.pricing import price_leg
from ...desk.snapshot import ExecutionSnapshot
from ..constants import SIDE_SELL, RefusalReason
from ..contracts.decisions import OpenPosition
from .desk_view import SchoolLeg, school_legs

Taken = Mapping[tuple[str, str], int]  # (contract, touch side) -> units already taken by this account here


class GateDisagrees(RuntimeError):
    """E4c/E4d and the school's naming of its findings disagree: a bug, never a fill."""


def entry_refusals(snapshot: ExecutionSnapshot, legs: tuple[SchoolLeg, ...], taken: Taken,
                   unmeasured: frozenset[str] = frozenset()) -> tuple[RefusalReason, ...]:  # fmt: skip
    """Every reason the entry cannot fill at this snapshot, each once, in a fixed order; empty when it may fill.
    `unmeasured`: the contracts whose quote E4 sees without a size only because none was measured
    (`desk_view.size_unmeasured`)."""
    found: list[RefusalReason] = []
    for leg in legs:
        found.append(_side_reason(snapshot, leg, True, taken, unmeasured))
        if leg.desk.protective and not found[-1]:
            found.append(_side_reason(snapshot, leg, False, taken, unmeasured))
    reasons = tuple(dict.fromkeys(r for r in found if r))
    authority = any(entry_problems(snapshot, [leg.desk], leg.units, taken) for leg in legs)  # per leg, as E4c checks
    if authority != bool(reasons):
        raise GateDisagrees(f"E4c/E4d and the school gate disagree at {snapshot.snapshot_id}: {reasons}")
    return reasons


def _side_reason(snapshot: ExecutionSnapshot, leg: SchoolLeg, opening: bool, taken: Taken,
                 unmeasured: frozenset[str]) -> RefusalReason | None:  # fmt: skip
    side = leg.desk.side(opening)
    priced = price_leg(snapshot, leg.desk, side, leg.units + taken.get((leg.desk.contract, side), 0))
    if priced.fills:
        return None
    if priced.quote is None:
        return RefusalReason.MISSING_QUOTE
    if leg.desk.contract in unmeasured:
        return RefusalReason.SIZE_NOT_MEASURED
    if priced.quote.a4_problem:
        return RefusalReason.ONE_SIDED_QUOTE
    return RefusalReason.SIZE_ABOVE_DISPLAYED if opening else RefusalReason.PROTECTION_UNSELLABLE


def taken_at_snapshot(underlying: str, positions: Iterable[OpenPosition]) -> Taken:
    """E4d's count for one account: each position's opening units by touch side, plus each protective leg's
    sell-back need on the bid. The caller passes only the positions entered at this snapshot."""
    taken: Counter[tuple[str, str]] = Counter()
    for position in positions:
        for leg in school_legs(underlying, position.legs, position.lot):
            taken[(leg.desk.contract, leg.desk.side(opening=True))] += leg.units
            if leg.desk.protective:
                taken[(leg.desk.contract, SIDE_SELL)] += leg.units
    return dict(taken)
