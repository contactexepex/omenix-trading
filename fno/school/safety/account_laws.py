"""Laws 1, 4 and 7 (story 3.3): a protected structure, the daily stop and the driver brake. Each reads; none changes
a proposal. The stop and the brake act when the loss reaches their limit (story 3.3: "reaches", "falls ... below"; C2's
own brake acts at its limit too): they pass one rupee short of it.

- Law 1 (C4's naked-leg rule, B2's `require_covered`): every sold leg covered by bought legs of the same type and
  expiry, lot for lot. Legs on two expiries are refused: calendars have no payoff or margin model (probe 5).
- Law 4: the realised plus marked loss since the previous session's slot stops new entries for the session. Exits
  are never laws' business: the fill port closes at valid two-sided quotes whatever the stop says.
- Law 7 (owner, 22 Oct 2026): a version whose equity falls `brake_rs` below its high opens nothing, from this
  decision until a monthly review row lifts it (the account view holds the latch); exits continue."""

from datetime import date

from ...research_engine.structures import BOUGHT, SOLD, Leg, NakedShortLeg, require_covered
from ..constants import SIDE_BUY, RefusalReason
from ..contracts.decisions import Proposal
from ..contracts.safety import AccountView, LawResult
from ..contracts.snapshot import SlotSnapshot


class ProtectedLaw:
    name = "protected"

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        expiries = {leg.key.expiry for leg in proposal.legs}
        units = [Leg(leg.key.strike, str(leg.key.kind), BOUGHT if leg.side == SIDE_BUY else SOLD)
                 for leg in proposal.legs for _ in range(leg.lots)]  # fmt: skip
        try:
            require_covered(units)
        except NakedShortLeg:
            return LawResult(self.name, False, RefusalReason.UNPROTECTED)
        passed = len(expiries) == 1
        return LawResult(self.name, passed, None if passed else RefusalReason.UNPROTECTED)


class DailyStopLaw:
    name = "daily_stop"

    def __init__(self, limit_rs: float):
        self.limit_rs = limit_rs

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        loss = account.loss_since_previous_slot
        passed = loss < self.limit_rs
        return LawResult(self.name, passed, None if passed else RefusalReason.DAILY_STOP, self.limit_rs, loss)


class BrakeLaw:
    name = "brake"

    def __init__(self, limit_rs: float):
        self.limit_rs = limit_rs

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        drawdown = account.equity_high - account.equity
        engaged, lifted = account.brake_engaged_on, account.brake_lifted_on
        latched = engaged is not None and engaged <= session and (lifted is None or lifted < engaged)
        passed = not latched and drawdown < self.limit_rs
        return LawResult(self.name, passed, None if passed else RefusalReason.BRAKE, self.limit_rs, drawdown)
