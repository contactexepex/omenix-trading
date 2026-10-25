"""The owner's limits and the account-wide risk checks, one class each (story C2; the drawdown brake is in
`drawdown.py`). Every limit comes from `config.yaml` `risk`; a rule passes at its limit and refuses beyond it."""

from __future__ import annotations

from collections.abc import Sequence

from .inputs import Market, Proposal, RiskBook
from .margins import StressedMargin
from .settings import ExposureSettings, Scenario
from .stress import Shock, ShockResult, StressEngine, stress_positions
from .trade_costs import TradeCosts
from .verdict import RiskRule, RiskVerdict, rupees


class MaxLossPerTrade(RiskRule):
    """The proposal's modelled maximum loss, every charge and pad included (B2's model), at most the limit."""

    name = "max_loss_per_trade"

    def __init__(self, costs: TradeCosts, limit_rs: float):
        self.costs, self.limit_rs = costs, limit_rs

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        loss = self.costs.max_loss(proposal, market)
        ok = loss <= self.limit_rs
        relation = "within" if ok else "above"
        reason = f"maximum loss {rupees(loss)} incl. costs is {relation} the limit {rupees(self.limit_rs)}"
        return self.verdict(ok, reason, max_loss_rs=loss, limit_rs=self.limit_rs)


class MaxOpenTrades(RiskRule):
    name = "max_open_trades"

    def __init__(self, limit: int):
        self.limit = limit

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        open_now = len(book.open_trades)
        ok = open_now + 1 <= self.limit
        reason = f"{open_now} open; this trade would make {open_now + 1} of at most {self.limit}"
        return self.verdict(ok, reason, open_trades=open_now, limit=self.limit)


class StressLoss(RiskRule):
    """Combined stress loss of the book's open trades (from their marks) plus the proposal (from its entry), in the
    worst configured scenario, at most the limit."""

    name = "stress_loss"

    def __init__(self, engine: StressEngine, costs: TradeCosts, scenarios: Sequence[Scenario], limit_rs: float):
        self.engine, self.costs, self.limit_rs = engine, costs, limit_rs
        self.shocks = tuple(Shock.of(s) for s in scenarios)

    def results(self, proposal: Proposal, book: RiskBook, market: Market) -> list[ShockResult]:
        positions = stress_positions(book, proposal, self.costs.entry_cash_flow(proposal, market))
        return self.engine.run(positions, market, self.shocks)

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        results = self.results(proposal, book, market)
        worst = max(results, key=lambda r: r.counted_loss)
        scenarios = {
            r.shock.name: {
                "counted_rs": r.counted_loss,
                "from_marks_rs": r.loss_from_marks,
                "from_entry_rs": r.loss_from_entry,
            }
            for r in results
        }
        ok = worst.counted_loss <= self.limit_rs
        relation = "within" if ok else "above"
        reason = f"worst scenario {worst.shock.name}: {rupees(worst.counted_loss)}, {relation} {rupees(self.limit_rs)}"
        return self.verdict(
            ok,
            reason,
            worst=worst.shock.name,
            worst_loss_rs=worst.counted_loss,
            limit_rs=self.limit_rs,
            scenarios=scenarios,
        )


class ExposureLimit(RiskRule):
    """Design 8.1, by full repricing: the account's loss from a NIFTY move either way and from an implied-volatility
    rise, today (no time passes), every position valued from its mark (pure sensitivity, without entry costs)."""

    name = "exposure_limit"

    def __init__(self, engine: StressEngine, settings: ExposureSettings):
        self.engine, self.settings = engine, settings
        move, points = settings.nifty_move_pct, settings.iv_rise_points
        self.move_shocks = (Shock(f"nifty_up_{move:g}pct", move), Shock(f"nifty_down_{move:g}pct", -move))
        self.iv_shock = Shock(f"iv_up_{points:g}points", 0.0, iv_add=points / 100)

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        positions = stress_positions(book, proposal)
        results = self.engine.run(positions, market, (*self.move_shocks, self.iv_shock))
        move_loss = max(r.loss_from_marks for r in results[:2])
        iv_loss = results[2].loss_from_marks
        s, problems = self.settings, []
        if move_loss > s.max_move_loss_rs:
            problems.append(f"{s.nifty_move_pct:g}% move loss {rupees(move_loss)} above {rupees(s.max_move_loss_rs)}")
        if iv_loss > s.max_iv_loss_rs:
            problems.append(
                f"{s.iv_rise_points:g}-point IV rise loss {rupees(iv_loss)} above {rupees(s.max_iv_loss_rs)}"
            )
        reason = (
            "; ".join(problems) or f"move loss {rupees(move_loss)} and IV-rise loss {rupees(iv_loss)} within limits"
        )
        return self.verdict(
            not problems,
            reason,
            move_loss_rs=move_loss,
            iv_rise_loss_rs=iv_loss,
            max_move_loss_rs=s.max_move_loss_rs,
            max_iv_loss_rs=s.max_iv_loss_rs,
        )


def _value(units, market: Market) -> float:
    """A position's value at today's mids, bought units plus."""
    return sum(n * market.quote(contract).mid for contract, n in units.items())


class MarginRoom(RiskRule):
    """Stressed margin of every open trade plus the proposal at most the available cash after the proposal's entry:
    min(cash, marked equity) - premium reserved, each moved by the entry (its cash flow, and its marked value), and
    never more than cash + the entry's cash flow + each trade's own liability (the value of every trade worth less than
    zero, the proposal's included). A broker does not net one trade's value against another's liability: with an open
    credit trade and a new debit trade, min(cash, marked equity) alone left the debit's premium free a second time
    (A14, judge 75's test).

    And the funds at entry (judge 77 addendum 3): Groww takes the margin without any credit for the sold premium, plus
    the bought premium and charges, from the free cash before the entry (the open trades' margins still blocked). The
    trade passes only when both hold, so C2 is never looser than that broker."""

    name = "margin_room"

    def __init__(self, stressed: StressedMargin, costs: TradeCosts):
        self.stressed, self.costs = stressed, costs

    def check(self, proposal: Proposal, book: RiskBook, market: Market) -> RiskVerdict:
        margins = {t.trade_id: self.stressed.margin(t.terms, market.day) for t in book.open_trades}
        margins[proposal.trade_id] = self.stressed.margin(proposal.terms, market.day)
        cash_flow = self.costs.entry_cash_flow(proposal, market)
        marked = sum(units * market.quote(c).mid for c, units in proposal.signed_units().items())
        state = book.state
        held_liabilities = sum(min(0.0, _value(t.units, market)) for t in book.open_trades)
        liabilities = held_liabilities + min(0.0, marked)
        lower = min(
            state.cash + cash_flow, state.marked_equity + cash_flow + marked, state.cash + cash_flow + liabilities
        )
        after = lower - state.premium_reserved
        needed = sum(margins.values())
        funds = self.costs.entry_funds(proposal, market)
        at_entry = sum(margins.values()) - margins[proposal.trade_id] + funds
        own_at_entry = self.stressed.margin_at_entry(proposal.terms, market.day)
        at_entry += own_at_entry
        capital = capital_at_entry(self.stressed.broker_margin(proposal.terms, market.day), funds, own_at_entry)
        free = min(state.cash, state.marked_equity, state.cash + held_liabilities) - state.premium_reserved
        ok = needed <= after and at_entry <= free
        reason = (
            f"stressed margin {rupees(needed)} is {_relation(needed, after)} available cash {rupees(after)} after "
            f"entry; at entry {rupees(at_entry)} (margin with no sold-premium credit + bought premium and charges "
            f"{rupees(funds)}) is {_relation(at_entry, free)} free cash {rupees(free)} before entry"
        )
        return self.verdict(
            ok,
            reason,
            stressed_margin_rs=margins,
            needed_rs=needed,
            available_after_entry_rs=after,
            available_before_rs=state.available_cash,
            funds_at_entry_rs=funds,
            needed_at_entry_rs=at_entry,
            free_before_entry_rs=free,
            capital_rs={proposal.trade_id: capital},
            **self.stressed.record(market.day),
        )


def capital_at_entry(broker_margin: float, premium_paid: float, margin_at_entry: float) -> dict[str, float]:
    """The trade's money at entry, split (story STR1b, review 100 point 2): what a broker blocks unstressed, the premium
    and charges paid, the owner's stress reserve on top, and their total. `capital_tied` (broker margin plus premium
    paid) is what scoreboard B counts; the stress reserve is a safety margin, never capital tied."""
    reserve = margin_at_entry - broker_margin
    return {
        "broker_margin": broker_margin, "premium_paid": premium_paid, "stress_reserve": reserve,
        "total_funds": broker_margin + premium_paid + reserve, "capital_tied": broker_margin + premium_paid,
    }  # fmt: skip


def _relation(needed: float, available: float) -> str:
    return "within" if needed <= available else "above"
