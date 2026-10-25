"""Laws 2 and 3 (story 3.3) on C2's own rule classes, unedited (story MS-P1d): the maximum loss per trade, and the
bucket, open-risk, new-risk-per-session and margin-room caps, each on the driver version's own account. A rule that
cannot check its input (C2's `RiskInputError`: an unmapped bucket, a missing mid or margin row) refuses: fail closed.

Law 2 takes the largest of three maximum losses, so the Rs 10,000 cap holds on what the fill can really lose: the
proposal's own figure, C2's (B2's model at this slot's mids with the Rs 1 pad) and B2's model at the touch the fill
will take (ask to buy, bid to sell) with the pad. At the touch the spread is paid, which the mid does not show."""

from collections.abc import Callable, Mapping
from datetime import date

from ...research_engine.cycle_costs import PAD, CycleTerms, PositionCosts
from ...research_engine.structures import NakedShortLeg
from ...risk.inputs import Proposal as RiskProposal
from ...risk.inputs import RiskInputError
from ...risk.rules import MaxLossPerTrade
from ...risk.verdict import RiskRule, RiskVerdict
from ..constants import SIDE_BUY, RefusalReason, RoadCode
from ..contracts.decisions import Proposal
from ..contracts.safety import AccountView, LawResult
from ..contracts.snapshot import SlotSnapshot
from .c2_inputs import c2_inputs

UNCHECKABLE = (RiskInputError, NakedShortLeg)  # C2 or B2 cannot measure it: the law refuses
Numbers = Callable[[RiskVerdict], tuple[float | None, float | None]]  # (limit, value) from a verdict's numbers


class C2Law:
    """One C2 rule as a school law. `slot` is every road's snapshot of this slot (read-only), so a position held on
    another road is marked at its own road's quotes."""

    def __init__(self, name: str, rule: RiskRule, reason: RefusalReason, numbers: Numbers,
                 slot: Mapping[RoadCode, SlotSnapshot], unchecked_note: str = ""):  # fmt: skip
        self.name, self.rule, self.reason, self.numbers, self.slot = name, rule, reason, numbers, dict(slot)
        self.unchecked_note = unchecked_note  # with it, an input C2 cannot check is refused with this note and why

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        try:
            inputs = c2_inputs(proposal, snapshot.road, account, {**self.slot, snapshot.road: snapshot}, session)
            verdict = self.rule.check(inputs.proposal, inputs.book, inputs.market)
        except UNCHECKABLE as unusable:
            note = f"{self.unchecked_note}{unusable}" if self.unchecked_note else ""
            return LawResult(self.name, False, self.reason, note=note)
        limit, value = self.numbers(verdict)
        return LawResult(self.name, verdict.ok, None if verdict.ok else self.reason, limit, value)


def cap_numbers(verdict: RiskVerdict) -> tuple[float | None, float | None]:
    totals = [group["total_rs"] for group in verdict.numbers["groups"].values()]
    return verdict.numbers["limit_rs"], max(totals, default=None)


def margin_numbers(verdict: RiskVerdict) -> tuple[float | None, float | None]:
    return verdict.numbers["available_after_entry_rs"], verdict.numbers["needed_rs"]


class MaxLossLaw:
    name = "max_loss"

    def __init__(self, limit_rs: float, charges: Mapping[str, float], c2: MaxLossPerTrade):
        self.limit_rs, self.charges, self.c2 = limit_rs, dict(charges), c2

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        try:
            inputs = c2_inputs(proposal, snapshot.road, account, {snapshot.road: snapshot}, session)
            at_mids = self.c2.check(inputs.proposal, inputs.book, inputs.market).numbers["max_loss_rs"]
            at_touch = self._at_touch(proposal, snapshot, inputs.proposal)
        except UNCHECKABLE:
            return LawResult(self.name, False, RefusalReason.MAX_LOSS, self.limit_rs)
        loss = max(proposal.max_loss, at_mids, at_touch)
        passed = loss <= self.limit_rs
        return LawResult(self.name, passed, None if passed else RefusalReason.MAX_LOSS, self.limit_rs, loss)

    def _at_touch(self, proposal: Proposal, snapshot: SlotSnapshot, risk: RiskProposal) -> float:
        prices = []
        for leg in proposal.legs:
            quote = snapshot.quote(leg.key)
            touch = None if quote is None or not quote.two_sided else quote.ask if leg.side == SIDE_BUY else quote.bid
            if touch is None:
                raise RiskInputError(f"no touch for {leg.key}")
            prices.append(touch)
        costs = PositionCosts(CycleTerms(lot=risk.units, charges=self.charges, pad=PAD))
        return costs.max_loss([p.leg for p in risk.legs], prices)
