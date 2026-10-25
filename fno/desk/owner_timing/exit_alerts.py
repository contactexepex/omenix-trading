"""The exit alert (story E8 rule 1): when E4's exit review orders an exit in an owner-timing view, the owner is told the
trade and the action at #fno-desk, never a price (the card rule of 15 Oct 2026), and the position stays open for the
owner-timing fill. The alert's Slack server time is the exit's order time T, so it is kept as a delivery record; an
alert that was not delivered is sent again at the next run, and T is its first delivery."""

from __future__ import annotations

import re

from ...cards.posting import CardPoster
from ...constants import OUTCOME_EXIT_ORDERED
from ..exit_timing import ExitTiming
from ..exits import ExitResult
from .timing_log import TimingLog

EXIT_ALERT = "F&O paper desk {book}: EXIT trade {trade_id} ({why}). Close it at the next session's open."
WAITING = "exit alert delivered at {at}: filled at its owner-timing due mark"
PLAIN_WORDS = re.compile(r"[a-z_ ]+")
GENERIC_WHY = "exit ordered"
UNDELIVERED = "exit alert NOT delivered ({outcome}): sent again at the next run"


def _why(reason: str) -> str:
    """The rule's name before the reason's first colon (profit_target, stop_loss, time_exit), only when it is plain
    words: anything else, which could carry a figure, gives the generic wording (the card rule: never a price)."""
    head = reason.split(":")[0].strip()
    return head if PLAIN_WORDS.fullmatch(head) else GENERIC_WHY


class AlertThenWait(ExitTiming):
    def __init__(self, poster: CardPoster, log: TimingLog):
        self.poster, self.log = poster, log

    def defer(self, book, position, snapshot, journal) -> ExitResult:
        trade_id = position.trade_id
        delivered = self.log.alert_time(book, trade_id)
        if delivered is None:
            ordered = [
                e["reason"] for e in journal.records.event_rows(trade_id) if e["outcome"] == OUTCOME_EXIT_ORDERED
            ]
            receipt = self.poster.post(EXIT_ALERT.format(book=book, trade_id=trade_id, why=_why(ordered[0])))
            if receipt.server_time is None:
                return ExitResult(trade_id, OUTCOME_EXIT_ORDERED, UNDELIVERED.format(outcome=receipt.outcome))
            delivered = receipt.server_time
            self.log.alerted(book, trade_id, delivered)
        return ExitResult(trade_id, OUTCOME_EXIT_ORDERED, WAITING.format(at=delivered.isoformat()))
