"""The account-level caps of design 6.2 (story C5), one rule class each, on the account's maximum losses.

Each cap adds the proposal's maximum loss to the maximum losses already counted in its group and passes at its limit,
refusing beyond it, as C2's rules do. A cap only refuses: it never resizes a proposal, so it can never enlarge a trade.
- Bucket cap: one group per bucket of the proposal; a position in two buckets (a directional spread, owner 15 Oct 2026
  "1 B") counts its full maximum loss in each, and every one of the proposal's buckets must be within the cap.
- Open-risk cap: every open position once.
- New risk per session: every trade first filled this session, open or already closed (owner, "3 A"), at the largest
  maximum loss it carried that day.
An unmapped bucket, a held position that is not defined risk, or a book whose session trades are unknown is an input
error, and the trade is refused (design 6.1a: fail closed). The paper-account rule refuses every trade of a book that
holds any other capital than its profile's `paper_account_rs` (its opening plus top-ups, story E1b), so an account
opened on the old Rs 5 lakh is never traded on silently.
"""

from __future__ import annotations

from abc import abstractmethod

from .inputs import Market, Proposal, RiskBook, RiskInputError
from .open_risk import PositionRisk, PositionRisks
from .verdict import RiskRule, RiskVerdict, rupees

Group = tuple[str, dict[str, float]]  # (what is counted, trade -> maximum loss), the proposal's included


class MaxLossCap(RiskRule):
    """Every group's maximum losses, the proposal's included, at most the limit."""

    def __init__(self, risks: PositionRisks, limit_rs: float):
        self.risks, self.limit_rs = risks, limit_rs

    @abstractmethod
    def groups(self, own: PositionRisk, book: RiskBook, market: Market) -> list[Group]:
        """The groups this cap checks, each with the proposal's maximum loss in it."""

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        own = self.risks.of_proposal(proposal, market)
        totals = [(what, counted, sum(counted.values())) for what, counted in self.groups(own, book, market)]
        ok = all(total <= self.limit_rs for _, _, total in totals)
        parts = [
            f"{what}: maximum losses {rupees(total)} with this trade's {rupees(own.max_loss_rs)} are "
            f"{'within' if total <= self.limit_rs else 'above'} the cap {rupees(self.limit_rs)}"
            for what, _, total in totals
        ]
        numbers = {what: {"total_rs": total, "counted_max_loss_rs": counted} for what, counted, total in totals}
        return self.verdict(
            ok, "; ".join(parts), proposal_max_loss_rs=own.max_loss_rs, limit_rs=self.limit_rs, groups=numbers
        )


class BucketCap(MaxLossCap):
    """Each of the proposal's buckets (design 6.2: Rs 30,000, the old 3-trade limit applied per correlated group)."""

    name = "bucket_cap"

    def groups(self, own: PositionRisk, book: RiskBook, market: Market) -> list[Group]:
        held = [self.risks.of_open(trade, market) for trade in book.open_trades]
        return [
            (f"bucket {bucket}", {p.trade_id: p.max_loss_rs for p in held if bucket in p.buckets} | _own(own))
            for bucket in own.buckets
        ]


class OpenRiskCap(MaxLossCap):
    """The whole book's open maximum losses (Rs 1.5 lakh): a cap on new entries, never a stop on open trades."""

    name = "open_risk_cap"

    def groups(self, own: PositionRisk, book: RiskBook, market: Market) -> list[Group]:
        held = [self.risks.of_open(trade, market) for trade in book.open_trades]
        return [("all open positions", {p.trade_id: p.max_loss_rs for p in held} | _own(own))]


class NewRiskPerDay(MaxLossCap):
    """The trades first filled this session, open or closed, at their largest maximum loss (Rs 50,000)."""

    name = "new_risk_per_day"

    def groups(self, own: PositionRisk, book: RiskBook, market: Market) -> list[Group]:
        if book.session_trades is None:
            raise RiskInputError(f"{book.name}: the trades of this session are not known")
        today = {t.trade_id: self.risks.of_session(t, market) for t in book.session_trades}
        return [("trades opened this session", today | _own(own))]


def _own(own: PositionRisk) -> dict[str, float]:
    return {own.trade_id: own.max_loss_rs}


class PaperAccountSize(RiskRule):
    """The book's capital (its opening plus top-ups in force, story E1b) is its profile's paper account (the books:
    Rs 20 lakh, owner 14 Oct 2026), no more and no less."""

    name = "paper_account"

    def __init__(self, paper_account_rs: float):
        self.paper_account_rs = paper_account_rs

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        opened = book.state.capital
        ok = opened == self.paper_account_rs
        reason = f"{book.name} has capital {rupees(opened)}; the paper account is {rupees(self.paper_account_rs)}" + (
            "" if ok else ": no trade until the owner decides how this account is reopened"
        )
        return self.verdict(ok, reason, capital_rs=opened, paper_account_rs=self.paper_account_rs)
