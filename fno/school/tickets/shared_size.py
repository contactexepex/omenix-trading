"""Shared displayed size (327 item 10): many paper accounts do not share one order book. Each account's fill is
priced on its own against the full displayed size (E4d per account), so a report must never sum fills that the same
displayed size could not have served together.

`allocate` serves whole fills, never part of one (fills are all legs or none), against what each contract and side
showed at one road's snapshot (orchestrator's rulings on judge 481, 22 Oct 2026):
- entries first, exits of held positions only from what is left (MS-P1d limit 2: an entry never counts on size an
  exit will take; an exit that finds too little waits);
- within entries and within exits, account fills first, tickets only from what is left: a ticket never takes an
  account's size;
- within each group, owners in an order seeded from SHA-256(session, slot, road), as RC1 is seeded, so no driver
  wins or loses by its name; the seed and the order are recorded; one owner's fills keep their given order.
An account entry the size could not serve is `unavailable: size_shared` (`fill_status`) and stays in every
denominator; the rupee sum leaves it out (`rupees.account_net`)."""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from ..constants import SIDE_BUY, Outcome, UnavailableReason
from ..contracts.accounts import FillResult
from ..contracts.decisions import Decision
from ..contracts.snapshot import ContractKey, SlotSnapshot
from ..execution.quote_rules import LIVE, QuoteRules


@dataclass(frozen=True)
class OwnedFill:
    owner: str  # the driver version whose fill it is
    fill: FillResult
    is_ticket: bool = False
    is_exit: bool = False


@dataclass(frozen=True)
class SizeAllocation:
    seed: str  # SHA-256 hex of "session|slot|road"
    order: tuple[str, ...]  # the owners in the order served: entries (accounts, then tickets), then exits
    servable: tuple[OwnedFill, ...]
    unservable: tuple[OwnedFill, ...]  # each would need size an earlier fill already used

    @property
    def unservable_fills(self) -> frozenset[tuple[str, FillResult]]:
        """(owner, fill): two accounts filling one structure at one touch give equal fills, so the owner names it."""
        return frozenset((owned.owner, owned.fill) for owned in self.unservable)


def allocation_seed(snapshot: SlotSnapshot, slot: str) -> str:
    return hashlib.sha256(f"{snapshot.session}|{slot}|{snapshot.road}".encode()).hexdigest()


def allocate(fills: Iterable[OwnedFill], snapshot: SlotSnapshot, slot: str, rules: QuoteRules = LIVE) -> SizeAllocation:
    """`fills`: every account and ticket fill (entries and exits) at this road's snapshot; refusals and states use
    no size and are left out. `rules`: d's one rule for a displayed size (live: an unmeasured or missing size serves
    nothing; practice: an unmeasured size has no limit); only a practice root passes practice rules."""
    seed = allocation_seed(snapshot, slot)
    filled = [owned for owned in fills if owned.fill.filled]
    ranked = sorted(filled, key=lambda o: (o.is_exit, o.is_ticket, _rank(seed, o.owner)))  # stable within one owner
    left: dict[tuple[ContractKey, str], int] = {}
    servable, unservable = [], []
    for owned in ranked:
        needs = [((leg.key, leg.side), leg.units) for leg in owned.fill.legs]
        for place, _ in needs:
            left.setdefault(place, _displayed(snapshot, rules, *place))
        if all(units <= left[place] for place, units in needs):
            for place, units in needs:
                left[place] -= units
            servable.append(owned)
        else:
            unservable.append(owned)
    order = tuple(dict.fromkeys(owned.owner for owned in ranked))
    return SizeAllocation(seed, order, tuple(servable), tuple(unservable))


def fill_status(decision: Decision, fill: FillResult, allocation: SizeAllocation) -> tuple[Outcome, str]:
    """A sealed trade's status after its entry fill: traded, `unavailable: size_shared`, or refused at the fill."""
    if decision.outcome != Outcome.TRADE:
        raise ValueError("only an account trade has a fill status")
    if not fill.filled:
        return Outcome.REFUSED, (fill.refused[0] if fill.refused else str(fill.state))
    if (decision.driver_id, fill) in allocation.unservable_fills:
        return Outcome.UNAVAILABLE, UnavailableReason.SIZE_SHARED
    return Outcome.TRADE, ""


def _rank(seed: str, owner: str) -> str:
    return hashlib.sha256(f"{seed}|{owner}".encode()).hexdigest()


def _displayed(snapshot: SlotSnapshot, rules: QuoteRules, key: ContractKey, side: str) -> float:
    quote = snapshot.quote(key)
    if quote is None:
        return 0
    bid, ask = rules.sizes(quote)
    return (ask if side == SIDE_BUY else bid) or 0  # no size is no fill, never unlimited
