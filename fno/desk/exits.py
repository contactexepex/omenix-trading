"""The exit review at each scheduled execution snapshot (story E4, design 8 and 9), for every open position of a book:

1. A leg that expired before its exit filled is cash-settled at its intrinsic value against NSE's final settlement
   price (story E7), with C1's settlement charges. Until the expiry day's file is published the position is
   `settlement_needed` (alert): it blocks the book's new risk and is never priced from a last or stale price.
2. A protective leg without a valid quote marks the position `protection_unverified` (the book opens no new risk while
   it is open) and orders its exit.
3. An exit already ordered, or an exit rule reached now, closes the position at this snapshot's valid quotes: short
   legs bought back first, protection sold last. A leg without a valid quote is a pending exit with an alert, retried
   at the next scheduled snapshot. The position is closed only when every exit fill is recorded.

When C3's data checks find the snapshot's prices unverified (stale, outside its window, not the pack's, a suspect
spot), no price is judged or filled from it: protection is not marked, price rules do not fire, and a due exit (ordered
or by the time rule) is a pending exit with an alert, filled at the next valid quotes. Expired legs still settle from
NSE's own file, which is not a quote.

Price rules are not judged at the snapshot that opened the position (its value there is only the spread just paid).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..alerts.sender import AlertSender
from ..books.equity import trade_positions
from ..checks.data_checks import CheckReport, DataChecks
from ..constants import (
    FILL_CLOSE,
    NIFTY_SYMBOL,
    OUTCOME_CLOSED,
    OUTCOME_EXIT_ORDERED,
    OUTCOME_PARTIAL_FILL,
    OUTCOME_PENDING_EXIT,
    OUTCOME_PROTECTION_UNVERIFIED,
    OUTCOME_SETTLEMENT_NEEDED,
)
from ..models import now_ist
from .execution import FillMaker, check_point_in_time, closing_quotes
from .exit_rules import ExitContext, ExitRule
from .exit_timing import ExitTiming, ImmediateExits
from .pricing import price_leg
from .records import DeskEvent, DeskJournal
from .settlement import SettlementError, SettlementPrices, settlement_record
from .snapshot import ExecutionSnapshot
from .status import OpenPosition, open_positions

HELD = "held"
NO_RULES = "no exit rules given for this open trade"
ALERT = "F&O paper desk {book}: trade {trade_id} {outcome}: {reason}"


def exit_decision_id(trade_id: str) -> str:
    """The decision ID an exit's fills and events carry: the trade's exit order."""
    return f"{trade_id}:{OUTCOME_EXIT_ORDERED}"


@dataclass(frozen=True)
class ExitResult:
    trade_id: str
    outcome: str
    reason: str
    alerts: tuple[str, ...] = ()  # each alert's send outcome


class ExitDesk:
    def __init__(self, charges: Mapping[str, float], alerts: AlertSender, settlements: SettlementPrices, clock=now_ist,
                 timing: ExitTiming | None = None):  # fmt: skip
        self.charges, self.alerts, self.settlements, self.clock = dict(charges), alerts, settlements, clock
        self.timing = timing or ImmediateExits()  # story E8: owner-timing views close at their own due mark

    def review(self, book: str, snapshot: ExecutionSnapshot, journal: DeskJournal,
               rules: Mapping[str, Sequence[ExitRule]], checks: CheckReport) -> list[ExitResult]:  # fmt: skip
        """Every open position at this snapshot; `checks` is C3's report on it."""
        check_point_in_time(snapshot, self.clock())
        DataChecks.require_for(checks, snapshot)
        positions = open_positions(journal.records)
        return [self._review(book, p, snapshot, journal, rules.get(p.trade_id), checks) for p in positions]

    def _review(self, book, position: OpenPosition, snapshot, journal, rules, checks: CheckReport) -> ExitResult:
        check_point_in_time(snapshot, self.clock(), not_before=position.last_fill_at)
        decision = exit_decision_id(position.trade_id)
        maker = FillMaker(book, position.strategy, decision, position.trade_id, snapshot, self.charges)
        if any(leg.expiry < snapshot.day for leg, _ in position.holdings):
            return self._settle(book, position, snapshot, journal)
        if checks.prices_unverified:
            return self._wait_for_valid_quotes(book, position, snapshot, journal, rules, checks)
        unquotable = [
            leg.contract for leg, units in position.holdings
            if leg.protective and not price_leg(snapshot, leg, leg.side(opening=False), units).fills
        ]  # fmt: skip
        alerts, reason = (), ""
        if unquotable:
            reason = f"{OUTCOME_PROTECTION_UNVERIFIED}: no valid quote for protective leg {', '.join(unquotable)}"
            marked = self._event(book, position, snapshot, journal, OUTCOME_PROTECTION_UNVERIFIED, reason,
                                 snapshot.snapshot_id)  # fmt: skip
            alerts = marked.alerts
        reason = position.exit_reason or reason
        if not reason and position.opened_by != snapshot.snapshot_id:
            if rules is None:
                return self._alert(book, position.trade_id, HELD, NO_RULES)
            reason = _reached(
                rules, position, ExitContext(snapshot.day, self._net_if_closed(position, snapshot, maker))
            )
        if not reason:
            return ExitResult(position.trade_id, HELD, "no exit rule reached")
        if not position.exit_reason:
            self._event(book, position, snapshot, journal, OUTCOME_EXIT_ORDERED, reason)
        result = self.timing.defer(book, position, snapshot, journal) or self._close(
            book, position, snapshot, journal, maker
        )
        return ExitResult(result.trade_id, result.outcome, result.reason, alerts + result.alerts)

    def _wait_for_valid_quotes(self, book, position: OpenPosition, snapshot, journal, rules, checks) -> ExitResult:
        """Prices unverified (C3): nothing is priced; only an ordered exit or the time rule (no price) can make the
        exit due, and a due exit is pending, with an alert, until the next valid quotes."""
        if rules is None and not position.exit_reason:
            return self._alert(book, position.trade_id, HELD, NO_RULES)
        reason = _due_without_prices(position, snapshot.day, rules)
        if not reason:
            return ExitResult(position.trade_id, HELD, checks.price_reason())
        if not position.exit_reason:
            self._event(book, position, snapshot, journal, OUTCOME_EXIT_ORDERED, reason)
        deferred = self.timing.defer(book, position, snapshot, journal)
        if deferred is not None:
            return deferred
        waiting = f"{checks.price_reason()} (retried at the next valid quotes)"
        return self._event(book, position, snapshot, journal, OUTCOME_PENDING_EXIT, waiting, snapshot.snapshot_id)

    @staticmethod
    def due_exits(journal: DeskJournal, day: date, rules: Mapping[str, Sequence[ExitRule]]) -> list[str]:
        """Open trades whose exit is due on `day` without any price (ordered, or the time rule), each with why: what
        the data gate names when no snapshot can be read (C3)."""
        due = [
            (p.trade_id, _due_without_prices(p, day, rules.get(p.trade_id))) for p in open_positions(journal.records)
        ]
        return [f"{trade_id} ({reason})" for trade_id, reason in due if reason]

    def _close(self, book, position: OpenPosition, snapshot, journal: DeskJournal, maker: FillMaker) -> ExitResult:
        closing, pending = closing_quotes(snapshot, position.holdings)
        for quote in closing:
            journal.record_fill(maker.record(quote, FILL_CLOSE))
        if pending:
            reason = "; ".join(f"{q.leg.contract}: {q.reason}" for q in pending) + " (retried at the next snapshot)"
            return self._event(book, position, snapshot, journal, OUTCOME_PENDING_EXIT, reason, snapshot.snapshot_id)
        return self.closed(book, position, snapshot, journal, "every leg closed")

    def _settle(self, book, position: OpenPosition, snapshot, journal: DeskJournal) -> ExitResult:
        """Expired legs close at NSE's final settlement (E7), one expiry at a time; a missing or unclear settlement
        price leaves the trade `settlement_needed`."""
        for expiry in sorted({leg.expiry for leg, _ in position.holdings if leg.expiry < snapshot.day}):
            try:
                final = self.settlements.final_settlement(NIFTY_SYMBOL, expiry)
                missing = f"NSE's F&O file of {expiry} (the final settlement price) is not published yet"
            except SettlementError as problem:
                final, missing = None, str(problem)
            if final is None:
                legs = ", ".join(leg.contract for leg, _ in position.holdings if leg.expiry == expiry)
                reason = f"{legs} expired on {expiry} before the exit filled: {missing}"
                return self._event(book, position, snapshot, journal, OUTCOME_SETTLEMENT_NEEDED, reason, snapshot.day)
            decision, trade_id = exit_decision_id(position.trade_id), position.trade_id
            for leg, units in (h for h in position.holdings if h[0].expiry == expiry):
                journal.record_fill(settlement_record(book, position.strategy, decision, trade_id, leg, units, final,
                                                      self.charges))  # fmt: skip
            how = f"settled at NSE's final settlement price {final.price:,.2f} ({final.source})"
        if trade_positions(journal.records.account.fills())[position.trade_id].is_open:
            return ExitResult(position.trade_id, HELD, how + "; legs of later expiries stay open")
        return self.closed(book, position, snapshot, journal, f"every leg closed, {how}")

    def pending(self, book, position: OpenPosition, snapshot, journal: DeskJournal, reason: str, once_per: str
                ) -> ExitResult:  # fmt: skip
        """A pending exit, recorded and alerted once per `once_per` (story E8's retries over the following marks)."""
        return self._event(book, position, snapshot, journal, OUTCOME_PENDING_EXIT, reason, once_per)

    def closed(self, book, position: OpenPosition, snapshot, journal: DeskJournal, how: str) -> ExitResult:
        net = trade_positions(journal.records.account.fills())[position.trade_id].cash_flow
        partial = any(e["outcome"] == OUTCOME_PARTIAL_FILL for e in journal.records.event_rows(position.trade_id))
        reason = f"{how}; net Rs {net:,.2f}"
        return self._event(book, position, snapshot, journal, OUTCOME_CLOSED, reason, cost=-net if partial else None)

    def _net_if_closed(self, position: OpenPosition, snapshot, maker: FillMaker) -> float | None:
        quotes = [price_leg(snapshot, leg, leg.side(opening=False), units) for leg, units in position.holdings]
        if not all(q.fills for q in quotes):
            return None
        return position.cash_flow + sum(maker.fill(q, FILL_CLOSE).amount for q in quotes)

    def _event(self, book, position, snapshot, journal, outcome, reason, once_per="", cost=None) -> ExitResult:
        """Record the event once (per snapshot or day when `once_per` is given); a new pending, unverified or settlement
        event is also sent as an alert."""
        event_id = ":".join(filter(None, (position.trade_id, outcome, str(once_per))))
        event = DeskEvent(event_id, snapshot.day, book, position.strategy, position.trade_id,
                          exit_decision_id(position.trade_id), snapshot.snapshot_id, snapshot.sha256, outcome, reason,
                          cost)  # fmt: skip
        new = journal.record_event(event)
        if new and outcome in (OUTCOME_PENDING_EXIT, OUTCOME_PROTECTION_UNVERIFIED, OUTCOME_SETTLEMENT_NEEDED):
            return self._alert(book, position.trade_id, outcome, reason)
        return ExitResult(position.trade_id, outcome, reason)

    def _alert(self, book: str, trade_id: str, outcome: str, reason: str) -> ExitResult:
        sent = self.alerts.send(ALERT.format(book=book, trade_id=trade_id, outcome=outcome, reason=reason))
        return ExitResult(trade_id, outcome, reason, (sent,))


def _reached(rules: Sequence[ExitRule], position: OpenPosition, context: ExitContext) -> str:
    """The first exit rule reached now, or empty."""
    return next((r for r in (rule.reached(position, context) for rule in rules) if r), "")


def _due_without_prices(position: OpenPosition, day: date, rules: Sequence[ExitRule] | None) -> str:
    """Why the exit is due with no price known: an exit already ordered, or a rule needing no price (the time rule)."""
    return position.exit_reason or _reached(rules or (), position, ExitContext(day, None))
