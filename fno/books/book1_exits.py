"""Book 1's exit rules (story E5, E3's `ExitRules` seam): each open trade exits by the time exit fixed at its decision
(the day D2 computed from the version file the run read, `book1_records.decided_exit_days`). E4 applies it; when C3
finds the prices unverified, E4 records the due exit as pending until valid quotes.

Nothing read now can stop or move that exit (judge 84). Today's version file is read only to alert: when it can no
longer be read, or states an exit code cannot enforce (D1 now refuses that for `paper`), the trade keeps its decided
time exit and #fno-desk is told. A trade with no opening record (story D3b: its run log is missing or mismatched)
gets no time exit, with an alert naming why, and E4 holds it; E4's own risk-reducing exits still run for it (design
9): protection unverified, expiry settlement and an exit already ordered. A record in another run naming the trade is
alerted at each review and never changes it."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date

from ..alerts.sender import AlertSender
from ..desk.daily_ports import ExitRules
from ..desk.exit_rules import ExitOnDay, ExitRule
from ..desk.records import DeskRecords
from ..desk.status import OpenPosition, open_positions
from ..playbook.documents import strategy_from_text
from ..playbook.exit_terms import unenforceable_exits
from .book1_records import DecidedExits

ALERT = "F&O paper desk {book} {trade} ({version}): {what}; its time exit {day} still runs"
UNREADABLE = "its playbook version file cannot be read now ({problem})"
NOT_ENFORCED = "its version states exits code cannot apply ({what})"
NO_RECORD = "F&O paper desk {book} {trade}: {why}; no time exit is set, so E4 holds it"
NO_RECORD_WHY = "no committed decision record names its time exit"
OTHER_RUNS = "F&O paper desk {book} {trade}: other runs name it ({runs}); the trade follows its opening run"


class PlaybookExitRules(ExitRules):
    def __init__(self, decided: Callable[[str], DecidedExits], version_text: Callable[[str], str | None],
                 records: Callable[[str], DeskRecords], alerts: AlertSender):  # fmt: skip
        self.decided, self.version_text, self.records, self.alerts = decided, version_text, records, alerts

    def rules(self, book: str) -> Mapping[str, Sequence[ExitRule]]:
        decided, rules = self.decided(book), {}
        for position in open_positions(self.records(book)):
            trade = position.trade_id
            if trade in decided.other_runs:
                self.alerts.send(OTHER_RUNS.format(book=book, trade=trade, runs=", ".join(decided.other_runs[trade])))
            if trade not in decided.exits:
                why = decided.problems.get(trade, NO_RECORD_WHY)
                self.alerts.send(NO_RECORD.format(book=book, trade=trade, why=why))
                continue
            exit_day, version = decided.exits[trade]
            rules[position.trade_id] = [ExitOnDay(exit_day, f"{version} time exit fixed at the decision")]
            self._warn(book, position, version, exit_day)
        return rules

    def _warn(self, book: str, position: OpenPosition, version: str, exit_day: date) -> None:
        """Alerts only: today's file never changes the exit above."""
        try:
            strategy = strategy_from_text(self.version_text(version) or "", f"{version}.yaml")
        except Exception as problem:  # noqa: BLE001 - any unreadable file is only reported, never fatal to the exits
            what = UNREADABLE.format(problem=f"{type(problem).__name__}: {problem}")
        else:
            unenforced = unenforceable_exits(strategy)
            what = NOT_ENFORCED.format(what="; ".join(unenforced)) if unenforced else ""
        if what:
            self.alerts.send(ALERT.format(book=book, trade=position.trade_id, version=version, what=what, day=exit_day))
