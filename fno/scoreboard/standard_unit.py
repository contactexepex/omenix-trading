"""Scoreboard A's standard unit (story S3; S1 `scoreboard_a_standardisation`), the one valuation F9 also imports: one
lot of each leg, entered at a day's execution snapshot by E4's pricing (the touch, all units or none) with C1's charges,
and exited by the version's time exit at that session's snapshot. A leg without a valid quote then is retried at each
next snapshot (E4's rule), dated the day it fills; a leg still open after its expiry is settled at E7's final
settlement price. No price is invented: an entry leg that does not fill leaves the unit "not filled"."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..accounting.ledgers import Order
from ..constants import NIFTY_SYMBOL, SIDE_BUY
from ..desk.pricing import DeskLeg, price_leg
from ..desk.settlement import SettlementError, SettlementPrices
from ..desk.snapshot import ExecutionSnapshot
from ..risk.inputs import RiskInputError
from ..risk.open_risk import HeldMaxLoss

CLOSED, OPEN, NOT_FILLED, MAX_LOSS_UNKNOWN = "closed", "open", "not filled", "maximum loss unknown"

Snapshots = Callable[[date], ExecutionSnapshot | None]  # a day's valid execution snapshot, None when there is none
SessionsBetween = Callable[[date, date], Sequence[date]]  # the sessions from the first day to the last, both included


@dataclass(frozen=True)
class StandardResult:
    status: str
    net: float | None = None  # rupees, every charge included; only when closed
    max_loss: float | None = None  # B2's model on the one-lot entry fills (story S3: never the record's figure)
    exited_on: date | None = None
    note: str = ""
    staggered: bool = False  # its legs exited on different sessions (E4's retry), disclosed (review 120)
    past_expiry: bool = False  # open with a leg past its expiry: settlement not available, so incomplete


def cash(order: Order, charges: Mapping[str, float]) -> float:
    """What one order moves (C1's `Order`, a traded fill or a cash settlement): premium or intrinsic value received
    for a sale, paid for a purchase, less its charges from the one charges model."""
    sign = -1 if order.side == SIDE_BUY else 1
    return sign * order.fill_price * order.units - sum(order.charges(dict(charges)).values())


class StandardUnit:
    def __init__(self, snapshots: Snapshots, sessions: SessionsBetween, settlements: SettlementPrices,
                 held: HeldMaxLoss, charges: Mapping[str, float], lot: int):  # fmt: skip
        self.snapshots, self.sessions, self.settlements = snapshots, sessions, settlements
        self.held, self.charges, self.lot = held, dict(charges), lot

    def value(self, legs: Sequence[DeskLeg], entry_day: date, exit_day: date, on: date) -> StandardResult:
        """The one-lot unit entered on `entry_day`, as known on `on`."""
        snapshot = self.snapshots(entry_day)
        quotes = [price_leg(snapshot, leg, leg.side(True), self.lot) for leg in legs] if snapshot else []
        missing = [q for q in quotes if not q.fills]
        if snapshot is None or missing:
            reason = "no valid execution snapshot" if snapshot is None else missing[0].reason
            return StandardResult(NOT_FILLED, note=reason)
        flow = sum(cash(Order(q.side, q.price, self.lot), self.charges) for q in quotes)
        try:
            max_loss = self.held.of_legs([(leg.leg, self.lot) for leg in legs], flow)
        except RiskInputError as problem:
            return StandardResult(MAX_LOSS_UNKNOWN, note=str(problem))
        return self._exit(list(legs), flow, max_loss, exit_day, on)

    def _exit(self, legs: list[DeskLeg], flow: float, max_loss: float, exit_day: date, on: date) -> StandardResult:
        exits: set[date] = set()
        for day in self.sessions(exit_day, on) if exit_day <= on else ():
            snapshot = self.snapshots(day)
            for leg in [leg for leg in legs if snapshot is not None and day <= leg.expiry]:
                quote = price_leg(snapshot, leg, leg.side(False), self.lot)
                if quote.fills:
                    flow = flow + cash(Order(quote.side, quote.price, self.lot), self.charges)
                    exits.add(day)
                    legs.remove(leg)
        note = ""
        for leg in [leg for leg in legs if leg.expiry < on]:
            try:
                final = self.settlements.final_settlement(NIFTY_SYMBOL, leg.expiry)
            except SettlementError as problem:  # a file without one clear price: open, never guessed (E7)
                final, note = None, f"; settlement refused: {problem}"
            if final is None:
                continue
            settled = Order(leg.side(False), leg.leg.intrinsic(final.price), self.lot, settlement=True)
            flow = flow + cash(settled, self.charges)
            exits.add(leg.expiry)
            legs.remove(leg)
        if legs:
            past = any(leg.expiry < on for leg in legs)
            note = f"{len(legs)} leg(s) still open{note}"
            return StandardResult(OPEN, max_loss=max_loss, note=note, past_expiry=past)
        return StandardResult(CLOSED, round(flow, 2), round(max_loss, 2), max(exits), staggered=len(exits) > 1)
