"""Story E2d: every open paper trade valued once a session, right after the exit review, by S2's rule imported
unchanged (`fno/scoreboard/daily_values.py`, hashed by S1): cash flow so far plus each held leg at the mid of the
session's recorded valid execution snapshot; a leg without one keeps its last valid mark from the trade's earlier
snapshots, flagged stale; a leg never marked leaves the trade unmarked. So the values equal scoreboard B's on every
session, and a lost marking day cannot make the two disagree: nothing is read back from what this step wrote.

Per account: the trades' rows (`trade_marks.csv`) and the session's equity row (closed equity plus the open trades'
values). An unmarked trade gets no price: its book's equity row is not written that session and one alert names it."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..alerts.sender import AlertSender
from ..books.account import PaperAccount
from ..books.equity import TradePosition, trade_positions
from ..books.trade_marks import AWAITING_SETTLEMENT, UNMARKED, VALUED, TradeMark, write_trade_marks
from ..constants import BOOKS
from ..scoreboard.daily_values import DayMarks, key_of, trade_days
from .daily_steps import ALERT, StepOutcome
from .pricing import DeskLeg
from .private_files import paper_accounts
from .records import DeskJournal

OpenJournal = Callable[[str], AbstractContextManager[DeskJournal]]  # an account's journal, locked, Drive-backed
Sessions = Callable[[date, date], list[date]]  # the NSE sessions from one day to another, both included
NOT_VALUED = "trade {trade} not valued: never validly quoted: {contracts}; no equity row for the book today"
FAILED = "MARKING FAILED: {error} (the other accounts are marked as usual)"


def marked_accounts(root: Path, books: Sequence[str]) -> list[str]:
    """The run's books and every registered shadow account (story R3), each in its own files; one not started yet
    has nothing to mark."""
    shadows = [a for a in paper_accounts(root) if a not in BOOKS]
    return [a for a in (*books, *shadows) if PaperAccount(root, a).started]


def mark_trade(position: TradePosition, legs: Mapping[str, DeskLeg], sessions: Sequence[date], marks: DayMarks,
               day: date) -> TradeMark:  # fmt: skip
    """The trade's mark on `day`, the last of `sessions` (its entry day to `day`)."""
    today = trade_days(position.fills, legs, sessions, marks)[-1]
    if today.value is None:
        return TradeMark(position.trade_id, UNMARKED, None, None, never_quoted(position, legs, sessions, marks))
    flow = sum(f.amount for f in position.fills if f.filled_at.date() <= day)
    past_expiry = any(legs[c].expiry < day for c in today.stale)
    status = AWAITING_SETTLEMENT if past_expiry else VALUED  # a label on S2's stale value, never another value
    return TradeMark(position.trade_id, status, today.value, today.value - flow, today.stale)


def never_quoted(position: TradePosition, legs: Mapping[str, DeskLeg], sessions: Sequence[date],
                 marks: DayMarks) -> tuple[str, ...]:  # fmt: skip
    """The held contracts with no valid mid on any session since each was first held: why it is unmarked."""
    held = sorted(c for c, units in position.units.items() if units)
    first = {c: min(f.filled_at.date() for f in position.fills if f.contract == c) for c in held}
    return tuple(c for c in held if all(key_of(legs[c]) not in marks(d) for d in sessions if d >= first[c]))


@dataclass(frozen=True)
class MarkedAccount:
    marks: tuple[TradeMark, ...]

    @property
    def unmarked(self) -> list[TradeMark]:
        return [m for m in self.marks if m.status == UNMARKED]

    def result(self) -> dict:
        return {"equity_row": not self.unmarked,
                "trades": [{"trade_id": m.trade_id, "status": m.status} for m in self.marks]}  # fmt: skip


class TradeMarker:
    """One session's marking of one account's open trades, inside its writer's lock."""

    def __init__(self, sessions: Sessions, marks: DayMarks):
        self.sessions, self.marks = sessions, marks

    def mark(self, journal: DeskJournal, day: date) -> MarkedAccount:
        account = journal.writer.account
        opened = [p for p in trade_positions(account.fills()).values() if p.is_open]
        marks = tuple(self._mark(journal, p, day) for p in opened)
        write_trade_marks(journal.writer, day, marks)
        marked = MarkedAccount(marks)
        if not marked.unmarked:
            stale = [c for m in marks for c in m.contracts]
            journal.writer.record_marked_equity(day, sum(m.value for m in marks), stale)
        return marked

    def _mark(self, journal: DeskJournal, position: TradePosition, day: date) -> TradeMark:
        sessions = self.sessions(position.fills[0].filled_at.date(), day)
        return mark_trade(position, journal.records.legs(position.trade_id), sessions, self.marks, day)


class MarkingStep:
    """The daily run's `trade_marks` step: each account in turn, in its journal under its single-writer lock, pulled
    from Drive and pushed back (what the fills' and exits' account write opens). Nothing is committed: marking
    changes no ledger row, so the public daily totals stay as they are, and a shadow account gets no public file.
    One account's failure is alerted and never stops another's (the exit review's per-book rule)."""

    def __init__(self, open_journal: OpenJournal, marker: Callable[[], TradeMarker],
                 accounts: Callable[[], Iterable[str]], alerts: AlertSender):  # fmt: skip
        self.open_journal, self.marker, self.accounts, self.alerts = open_journal, marker, accounts, alerts

    def run(self, day: date) -> StepOutcome:
        marker, result = self.marker(), {}
        for account in self.accounts():
            try:
                with self.open_journal(account) as journal:
                    marked = marker.mark(journal, day)
            except Exception as failure:  # noqa: BLE001 - one account's failure must not halt the others' marking
                error = f"{type(failure).__name__}: {failure}"
                result[account] = {"marked": False, "error": error}
                self.alerts.send(ALERT.format(day=day, book=account, what=FAILED.format(error=error)))
                continue
            result[account] = {"marked": True} | marked.result()
            for mark in marked.unmarked:
                what = NOT_VALUED.format(trade=mark.trade_id, contracts=", ".join(mark.contracts))
                self.alerts.send(ALERT.format(day=day, book=account, what=what))
        return StepOutcome({}, result)
