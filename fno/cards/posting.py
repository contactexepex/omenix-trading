"""Posting the card (story T1): `CardPoster` returns Slack's own server timestamp of the post (`ts`), the card's
issuance time (design 04 section 4.4), or why it was not sent. Only #fno-desk with `FNO_SLACK_BOT_TOKEN`. A failed post
is retried once; the outcome line uses the alert sender's wording ("alert NOT sent: <reason>"), never the token."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

from ..alerts.sender import NO_TOKEN, NOT_SENT, SENT, slack_post

ATTEMPTS = 2  # the post and one retry (design 4.1: "a failed post is retried and logged")
RETRY_PAUSE_SECONDS = 5.0
# Failures that mean Slack surely did not post (no connection was made, or Slack answered that it did not post): only
# these are retried, since chat.postMessage is not idempotent and a lost answer would otherwise post the card twice
NOT_DELIVERED = frozenset({"ConnectTimeout", "ratelimited", "service_unavailable"})
# Failures after the request may have gone out, where Slack may have posted the card although no usable answer came
# back (a plain ConnectionError includes a connection dropped after sending; judge 101 minor 3)
SENT_THEN_LOST = frozenset(
    {"ConnectionError", "ReadTimeout", "Timeout", "ChunkedEncodingError", "JSONDecodeError", "RequestsJSONDecodeError"}
)
UNKNOWN = "{failure}; Slack may still have posted it (check channel {channel}); not retried"  # the poster's own
NO_TS = "Slack accepted the post but gave no readable ts: posted, with no issuance time (not retried)"


@dataclass(frozen=True)
class PostReceipt:
    outcome: str  # the line to print
    ts: str | None = None  # Slack's message timestamp, set only when Slack accepted the post
    channel: str | None = None

    @property
    def sent(self) -> bool:
        return self.ts is not None

    @property
    def server_time(self) -> datetime | None:
        """Slack's server time of the post (its `ts` is seconds since 1970, UTC)."""
        return datetime.fromtimestamp(float(self.ts), UTC) if self.ts else None


class CardPoster(ABC):
    @abstractmethod
    def post(self, text: str) -> PostReceipt:
        """Post the card; never raises."""


class SlackCardPoster(CardPoster):
    def __init__(self, token: str, channel: str, session: requests.Session | None = None, sleep: Callable = time.sleep):
        self._token, self._channel = token, channel
        self._session, self._sleep = session or requests.Session(), sleep

    def post(self, text: str) -> PostReceipt:
        failure = None
        for attempt in range(ATTEMPTS):
            if attempt:
                self._sleep(RETRY_PAUSE_SECONDS)
            body, failure = slack_post(self._session, self._token, self._channel, text)
            if failure is None:  # accepted: never posted again, even without a usable ts
                return _accepted(body, self._channel)
            if _may_have_posted(failure):  # a retry could post the card twice
                return PostReceipt(NOT_SENT.format(reason=UNKNOWN.format(failure=failure, channel=self._channel)))
            if failure not in NOT_DELIVERED:  # Slack refused it (e.g. channel_not_found): retrying cannot help
                return PostReceipt(NOT_SENT.format(reason=failure))
        return PostReceipt(NOT_SENT.format(reason=f"{failure} after {ATTEMPTS} attempts"))


def _may_have_posted(failure: str) -> bool:
    return failure in SENT_THEN_LOST or failure.startswith("unexpected answer")


def _accepted(body: dict, channel: str) -> PostReceipt:
    """A post Slack accepted; without a readable `ts` it has no issuance time, which is said plainly."""
    try:
        ts = str(body["ts"])
        float(ts)
    except (KeyError, TypeError, ValueError):
        return PostReceipt(NOT_SENT.format(reason=NO_TS))
    return PostReceipt(SENT, ts, body.get("channel", channel))


class NoCardPoster(CardPoster):
    """Used when no Slack token is set: says so instead of failing silently."""

    def __init__(self, reason: str = NO_TOKEN):
        self._reason = reason

    def post(self, text: str) -> PostReceipt:
        return PostReceipt(NOT_SENT.format(reason=self._reason))
