"""Alert senders (``fno/shared/alerts``): the SENT / NOT-SENT contract with a fake Slack transport. No real Slack.

Why fakes matter here: a prior session posted to #fno-desk by reaching a live path. Every sender below is driven by
an injected fake, so nothing leaves the process."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from fno.shared.alerts.reported import ReportedAlerts
from fno.shared.alerts.sender import NOT_SENT, SENT, AlertSender, NoAlertSender, SlackChannelAlerts, slack_post

CHANNEL = "C0C89E8QCCD"


@dataclass
class _FakeSlackResponse:
    status_code: int = 200
    _body: object = None

    def json(self) -> object:
        return self._body


@dataclass
class _FakeSlackSession:
    """Records the one POST and returns a canned answer; never touches the network."""

    response: _FakeSlackResponse = field(default_factory=lambda: _FakeSlackResponse(_body={"ok": True}))
    posts: list[dict] = field(default_factory=list)

    def post(self, url, headers=None, json=None, timeout=None) -> _FakeSlackResponse:
        self.posts.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return self.response


class _StubSender(AlertSender):
    def __init__(self, outcome: str):
        self._outcome = outcome

    def send(self, text: str) -> str:
        return self._outcome


def test_slack_post_accepts_ok() -> None:
    session = _FakeSlackSession(_FakeSlackResponse(_body={"ok": True}))
    body, failure = slack_post(session, "fake-token", CHANNEL, "hello")
    assert failure is None and body == {"ok": True}
    assert session.posts[0]["json"] == {"channel": CHANNEL, "text": "hello"}


def test_slack_post_reports_error_without_leaking_token() -> None:
    session = _FakeSlackSession(_FakeSlackResponse(_body={"ok": False, "error": "channel_not_found"}))
    body, failure = slack_post(session, "fake-token", CHANNEL, "hi")
    assert body is None and failure == "channel_not_found"


def test_slack_channel_alerts_sent_path() -> None:
    sender = SlackChannelAlerts("fake-token", CHANNEL, session=_FakeSlackSession())
    assert sender.send("line") == SENT


def test_slack_channel_alerts_not_sent_path() -> None:
    session = _FakeSlackSession(_FakeSlackResponse(_body={"ok": False, "error": "not_authed"}))
    sender = SlackChannelAlerts("fake-token", CHANNEL, session=session)
    assert sender.send("line") == NOT_SENT.format(reason="not_authed")


def test_no_alert_sender_always_not_sent() -> None:
    assert NoAlertSender().send("anything").startswith("alert NOT sent")


def test_reported_alerts_prints_unsent_line() -> None:
    printed: list[str] = []
    reported = ReportedAlerts(_StubSender(NOT_SENT.format(reason="down")), out=printed.append)
    outcome = reported.send("the message")
    assert outcome == NOT_SENT.format(reason="down")
    assert printed == [f"{outcome} | the message"]  # routine can re-post this line


def test_reported_alerts_silent_on_sent() -> None:
    printed: list[str] = []
    reported = ReportedAlerts(_StubSender(SENT), out=printed.append)
    assert reported.send("ok") == SENT
    assert printed == []


def test_slack_post_handles_non_dict_body() -> None:
    session = _FakeSlackSession(_FakeSlackResponse(status_code=500, _body="gateway error"))
    body, failure = slack_post(session, "fake-token", CHANNEL, "hi")
    assert body is None and failure is not None


@pytest.mark.parametrize("outcome", [SENT, NOT_SENT.format(reason="x")])
def test_reported_alerts_returns_inner_outcome(outcome: str) -> None:
    assert ReportedAlerts(_StubSender(outcome), out=lambda _: None).send("m") == outcome
