"""Posting the 15:45 report (story FL1-1c): one Slack message to #fno-forecast with the 3 text lines, the picture and
the details file attached (owner, 21 Oct 2026: "all of them"). Slack's file upload has three calls: ask an upload
address for each file, send its bytes there, then complete the upload into the channel with the text. Nothing is
posted until the last call, so a failure before it is surely "not posted" (a rerun may try again); a lost answer to
the last call may have posted the message, so it is marked as possibly posted and never retried (no double post).
Only `FNO_SLACK_BOT_TOKEN`; the token never appears in an outcome line."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from ..alerts.sender import NO_TOKEN, NOT_SENT, SLACK_TIMEOUT_SECONDS

GET_URL = "https://slack.com/api/files.getUploadURLExternal"
COMPLETE_URL = "https://slack.com/api/files.completeUploadExternal"
POSTED = "posted to #fno-forecast"
MAYBE = "{failure}; Slack may still have posted it (check channel {channel}); not retried"
LOST_ANSWER = (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError, ValueError)


@dataclass(frozen=True)
class Attachment:
    name: str  # the file name Slack shows
    data: bytes
    title: str


@dataclass(frozen=True)
class Delivery:
    outcome: str  # the line to print
    sent: bool = False
    may_have_posted: bool = False  # the message may exist although no answer came: never post again


class ReportPoster(ABC):
    @abstractmethod
    def post(self, text: str, attachments: list[Attachment]) -> Delivery:
        """Post the message with its files; never raises."""


class NoReportPoster(ReportPoster):
    """Used when no Slack token is set: says so instead of failing silently."""

    def post(self, text: str, attachments: list[Attachment]) -> Delivery:
        return Delivery(NOT_SENT.format(reason=NO_TOKEN))


class SlackFilesPoster(ReportPoster):
    def __init__(self, token: str, channel: str, session: requests.Session | None = None):
        self._token, self._channel, self._session = token, channel, session or requests.Session()

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def _upload(self, attachment: Attachment) -> str:
        """The file's Slack id; raises `RuntimeError` with the reason when Slack refused it."""
        form = {"filename": attachment.name, "length": len(attachment.data)}
        answer = self._session.post(GET_URL, headers=self._auth(), data=form, timeout=SLACK_TIMEOUT_SECONDS).json()
        if not answer.get("ok"):
            raise RuntimeError(answer.get("error", "no upload address"))
        sent = self._session.post(answer["upload_url"], data=attachment.data, timeout=SLACK_TIMEOUT_SECONDS)
        if sent.status_code != 200:
            raise RuntimeError(f"upload refused (HTTP {sent.status_code})")
        return answer["file_id"]

    def post(self, text: str, attachments: list[Attachment]) -> Delivery:
        try:
            files = [{"id": self._upload(a), "title": a.title} for a in attachments]
        except (requests.RequestException, ValueError, KeyError, RuntimeError) as error:
            return Delivery(NOT_SENT.format(reason=str(error) if isinstance(error, RuntimeError)
                                            else type(error).__name__))  # fmt: skip
        try:
            answer = self._session.post(COMPLETE_URL, headers=self._auth(), timeout=SLACK_TIMEOUT_SECONDS,
                                        json={"files": files, "channel_id": self._channel,
                                              "initial_comment": text}).json()  # fmt: skip
        except requests.ConnectTimeout:  # no connection was made: surely not posted
            return Delivery(NOT_SENT.format(reason="ConnectTimeout"))
        except LOST_ANSWER as error:
            reason = MAYBE.format(failure=type(error).__name__, channel=self._channel)
            return Delivery(NOT_SENT.format(reason=reason), may_have_posted=True)
        except requests.RequestException as error:
            return Delivery(NOT_SENT.format(reason=type(error).__name__))
        if not isinstance(answer, dict) or not answer.get("ok"):
            return Delivery(NOT_SENT.format(reason=answer.get("error", "refused") if isinstance(answer, dict)
                                            else "unexpected answer"))  # fmt: skip
        return Delivery(POSTED, sent=True)
