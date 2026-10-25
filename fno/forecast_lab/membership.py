"""Criterion 7: the bot's membership in #fno-forecast and #fno-intraday, checked with Slack's read-only
`conversations.info` (its `channel.is_member`), never a test post. A go-live check before `forecast_lab.live_from`
is set; the token never appears in a line."""

from __future__ import annotations

import requests

from ..alerts.sender import SLACK_TIMEOUT_SECONDS
from ..constants import FNO_FORECAST_CHANNEL_ID, FNO_INTRADAY_CHANNEL_ID

CONVERSATIONS_INFO_URL = "https://slack.com/api/conversations.info"
LAB_CHANNELS = {"#fno-forecast": FNO_FORECAST_CHANNEL_ID, "#fno-intraday": FNO_INTRADAY_CHANNEL_ID}
MEMBER = "{name}: the bot is a member"
NOT_MEMBER = "{name}: the bot is NOT a member"
UNKNOWN = "{name}: membership unknown ({reason})"


def _is_member(session: requests.Session, token: str, channel: str) -> tuple[bool | None, str]:
    try:
        response = session.get(CONVERSATIONS_INFO_URL, headers={"Authorization": f"Bearer {token}"},
                               params={"channel": channel}, timeout=SLACK_TIMEOUT_SECONDS)  # fmt: skip
        body = response.json()
    except (requests.RequestException, ValueError) as error:
        return None, type(error).__name__
    if not isinstance(body, dict) or not body.get("ok"):
        return None, body.get("error", "no answer") if isinstance(body, dict) else "unexpected answer"
    return bool(body.get("channel", {}).get("is_member")), ""


def check_membership(session: requests.Session, token: str, channels=LAB_CHANNELS) -> tuple[list[str], bool]:
    """(one line per channel, True when the bot is a member of every one)."""
    lines, every = [], True
    for name, channel in channels.items():
        member, reason = _is_member(session, token, channel)
        every = every and member is True
        template = UNKNOWN if member is None else MEMBER if member else NOT_MEMBER
        lines.append(template.format(name=name, reason=reason))
    return lines, every
