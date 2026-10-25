"""Law 5, the quote gate (story 3.3), as one law per reason so every reason is kept: a leg with no quote, a leg
without a valid two-sided A4 quote, a live quote whose displayed size was never measured, an opening side whose
displayed size does not cover the units (with the units this account already took at this snapshot, E4d), and a
protective leg that cannot be sold back there (E4c). The one gate (`execution/entry_gate.py`, on E4's `price_leg` and
E4c/E4d's `entry_problems`) judges all five under the same `QuoteRules` as the fill port, so a proposal these laws pass
is one the fill can take.

Beside it, EDGE1's impossible-price rule: at the touch the fill would take, the position must be worth strictly more
than its worst payoff at expiry and strictly less than its best; anything else promises a trade that cannot lose or
cannot win, which only bad quotes do. And no leg of it may be impossible by b's own rule (`quality/prices.py`,
`impossible_keys`, judged among the proposal's legs): every vertical of one type and expiry must have a quoted range
that overlaps [0, width] within b's 1e-9 tolerance (owner's decision, 22 Oct 2026, between judges 486 add. 1 and
488.1: "ranges"), and no bid may sit above what the option can ever be worth. One rule for the gate and the law, so one
stale vertical never hides behind another in the total. It is judged once every leg has a touch; until then the gate
refuses."""

from datetime import date

from ...research_engine.structures import BOUGHT, SOLD, Leg, payoff_bounds, position_value
from ..constants import SIDE_BUY, RefusalReason
from ..contracts.decisions import Proposal
from ..contracts.roads import ROADS_BY_CODE
from ..contracts.safety import AccountView, LawResult
from ..contracts.snapshot import SlotSnapshot
from ..execution.desk_view import execution_snapshot, school_legs, size_unmeasured
from ..execution.entry_gate import entry_refusals, taken_at_snapshot
from ..execution.quote_rules import LIVE, PRACTICE_SIZE_NOTE, QuoteRules
from ..quality.prices import impossible_keys

GATE_REASONS = (
    RefusalReason.MISSING_QUOTE,
    RefusalReason.ONE_SIDED_QUOTE,
    RefusalReason.SIZE_NOT_MEASURED,
    RefusalReason.SIZE_ABOVE_DISPLAYED,
    RefusalReason.PROTECTION_UNSELLABLE,
)
SIZE_REASONS = frozenset({RefusalReason.SIZE_ABOVE_DISPLAYED, RefusalReason.PROTECTION_UNSELLABLE})


def gate_refusals(proposal: Proposal, account: AccountView, snapshot: SlotSnapshot,
                  rules: QuoteRules = LIVE) -> tuple[RefusalReason, ...]:  # fmt: skip
    underlying = ROADS_BY_CODE[snapshot.road].underlying
    here = [p for p in account.opened_this_session if p.road == snapshot.road and p.opened == snapshot.session]
    legs = school_legs(underlying, proposal.legs, proposal.lot)
    desk, unmeasured = execution_snapshot(snapshot, underlying, rules), size_unmeasured(snapshot, underlying, rules)
    return entry_refusals(desk, legs, taken_at_snapshot(underlying, here), unmeasured)


class QuoteGateLaw:
    def __init__(self, reason: RefusalReason, rules: QuoteRules = LIVE):
        if reason not in GATE_REASONS:
            raise ValueError(f"{reason} is not a quote-gate reason")
        self.reason, self.name, self.rules = reason, f"quote_gate:{reason}", rules

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        passed = self.reason not in gate_refusals(proposal, account, snapshot, self.rules)
        return LawResult(
            self.name, passed, None if passed else self.reason, note=self._note(passed, proposal, snapshot)
        )

    def _note(self, passed: bool, proposal: Proposal, snapshot: SlotSnapshot) -> str:
        """A size check passed under practice rules on a size nobody measured says it was not tested."""
        quotes = [snapshot.quote(leg.key) for leg in proposal.legs]
        untested = self.rules.practice and any(q is not None and not q.sizes_measured for q in quotes)
        return PRACTICE_SIZE_NOTE if passed and self.reason in SIZE_REASONS and untested else ""


class ImpossiblePriceLaw:
    name = "impossible_price"

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        legs, prices = [], []
        for leg in proposal.legs:
            quote = snapshot.quote(leg.key)
            if quote is None or not quote.two_sided:
                return LawResult(self.name, True, None)  # not judged: the quote gate refuses this entry
            bought = leg.side == SIDE_BUY
            for _ in range(leg.lots):
                legs.append(Leg(leg.key.strike, str(leg.key.kind), BOUGHT if bought else SOLD))
                prices.append(quote.ask if bought else quote.bid)
        lowest, highest = payoff_bounds(legs)
        value = position_value(legs, prices)
        if not lowest < value < highest:
            return LawResult(self.name, False, RefusalReason.IMPOSSIBLE_LEG_PRICE, None, value)
        flagged = impossible_keys(snapshot, among={leg.key for leg in proposal.legs})
        if flagged:
            return LawResult(self.name, False, RefusalReason.IMPOSSIBLE_LEG_PRICE, None, float(len(flagged)))
        return LawResult(self.name, True, None, None, value)
