"""The two issuance witnesses of a day's cards (design 04 section 4.4, story T1 criterion 6): Slack's server timestamp
of the post (stored in the delivery metadata) and GitHub's server-side push receipt of the commit that first added that
metadata (`PushReceipts`, story F1's reader). A commit's own date is set by whoever made it and is never read."""

from __future__ import annotations

from datetime import date, datetime

from ..ai.history import RepoHistory
from ..ai.receipts import PushReceipts, ReceiptAccessDenied, ReceiptUnknown
from ..models import IST
from .deliveries import DeliveryLog

NONE = "no committed card delivery for {day}"
LINE = "{path}: Slack {slack}; GitHub push receipt {github}"
NOT_POSTED = "not posted ({outcome})"
NOT_PUSHED = "none yet ({why})"
NO_ACCESS = "NOT READABLE: {why} (an access problem, not a missing receipt)"


def _shown(moment: datetime) -> str:
    return f"{moment.astimezone(IST):%Y-%m-%d %H:%M:%S} IST"


class IssuanceWitness:
    def __init__(self, deliveries: DeliveryLog, history: RepoHistory, receipts: PushReceipts):
        self.deliveries, self.history, self.receipts = deliveries, history, receipts

    def lines(self, day: date) -> list[str]:
        attempts = self.deliveries.attempts(day)
        if not attempts:
            return [NONE.format(day=day)]
        return [LINE.format(path=p, slack=_slack(m), github=self._github(p)) for p, m in attempts]

    def _github(self, path: str) -> str:
        commit = self.history.first_commit_adding(path)
        if commit is None:
            return NOT_PUSHED.format(why="the delivery file is not committed")
        try:
            return f"{_shown(self.receipts.received_at(commit))} (commit {commit[:10]})"
        except ReceiptAccessDenied as error:
            return NO_ACCESS.format(why=error)
        except ReceiptUnknown as error:
            return NOT_PUSHED.format(why=error)


def _slack(metadata: dict) -> str:
    slack = metadata.get("slack") or {}
    if not slack.get("sent") or not slack.get("server_time_utc"):
        return NOT_POSTED.format(outcome=slack.get("outcome", "no Slack outcome recorded"))
    return f"{_shown(datetime.fromisoformat(slack['server_time_utc']))} (ts {slack['ts']})"
