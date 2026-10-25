"""Home's F&O blocks (story P10, W10's contract): the three paper books' accounts (`FnoBooks`, "Who trades") and the
F&O picks panel (`FnoPicks`), each a pure function of the session's Home inputs. The picks panel shows the honest
empty state while no book has an approved strategy."""

from __future__ import annotations

from .blocks import CURRENCY, BlockBuilder, SessionRows
from .page_holds import PageHeld

DECISION_UTC = "T09:30:00Z"  # the books decide at 15:00 IST (design 13.5): their figures are as of then
# Story P11's hold reasons: fixed sentences shown on screen, so no value, no digit and no story code (contract 2.13.0;
# the screens lead's wording, one list with the contract's examples). The risk used is C2's stress of the open trades
# and the picks are the books' D3 decision records, neither built by story P10 yet.
OPEN_TRADE_RISK = (
    "A book holds an open trade whose risk this page cannot compute yet, so nothing is shown rather than a wrong figure"
)
APPROVED_PICKS = (
    "A strategy is approved, and this page cannot build its picks yet, so nothing is shown rather than an empty "
    "panel that is no longer true"
)


class FiguresNotComputed(RuntimeError):
    """A figure no page can be built without: the whole publication stops (Home's own two gaps are holds, P11)."""


class HeldWithoutRow(BlockBuilder):
    """A page held with no row (story P11): its old payload would state what the hold's rule says is no longer true."""

    def held(self, previous: dict, rule: str) -> None:
        return None


class FnoBooksBlock(HeldWithoutRow):
    page_key, served_schema = "risk", "FnoBooksResponse"  # W10: "pages risk and scoreboard_b"; the dashboard reads risk

    def build(self, rows: SessionRows) -> dict:
        home = rows.home
        books = []
        for b in home.books:
            if b.open_trades:
                raise PageHeld(OPEN_TRADE_RISK)
            books.append({
                "book": b.number, "family": b.family, "name": b.name, "value": b.value, "pnl": b.pnl,
                "approved": list(home.approved), "limit_used": 0.0, "limit_max": home.limit_max,
                "as_of": rows.day.isoformat() + DECISION_UTC,
            })  # fmt: skip
        return {"currency": CURRENCY, "books": books}


class FnoPicksBlock(HeldWithoutRow):
    page_key, served_schema = "today", "FnoPicksResponse"  # W10: "fno.pages_history page today (P1)"

    def build(self, rows: SessionRows) -> dict:
        home = rows.home
        if home.approved:
            raise PageHeld(APPROVED_PICKS)
        return {"currency": CURRENCY, "fno_state": {"approved": False, "note": home.approval_note}, "rows": [],
                "baskets": {}}  # fmt: skip
