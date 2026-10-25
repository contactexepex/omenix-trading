"""How a chosen trade changes the book that later candidates are checked against (story D2: candidates compete for
slots and cash in rank order, each taking its money before the next is considered). Computed with C2's own cost model
and the day's marks, so the next candidate's risk checks see the account as it would be after the entry."""

from __future__ import annotations

from dataclasses import replace

from ..risk.inputs import Market, OpenTrade, Proposal, RiskBook, SessionTrade
from ..risk.trade_costs import TradeCosts


def book_after_entry(book: RiskBook, proposal: Proposal, market: Market, costs: TradeCosts) -> RiskBook:
    cash_flow = costs.entry_cash_flow(proposal, market)
    units = proposal.signed_units()
    marked = sum(count * market.quote(contract).mid for contract, count in units.items())
    state = book.state
    state = replace(
        state,
        cash=state.cash + cash_flow,
        open_value=state.open_value + marked,
        marked_equity=state.marked_equity + cash_flow + marked,
        open_trades=state.open_trades + 1,
    )
    trade = OpenTrade(proposal.trade_id, proposal.terms, units, cash_flow)
    session = book.session_trades
    if session is not None:  # chosen this session: new risk today (story C5)
        session = (*session, SessionTrade(proposal.trade_id, ((units, cash_flow),)))
    return replace(book, state=state, open_trades=(*book.open_trades, trade), session_trades=session)
