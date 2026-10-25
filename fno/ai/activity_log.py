"""GitHub's push log of `main` (`GET /repos/{owner}/{repo}/activity`), read newest first and only as far back as a
question needs (story receipts-reach). Its pages are kept, so a second question reads only the pages the first did not.

This repository pushes about 270 times a day (measured 22 Oct 2026: 1,903 pushes in a week), so a fixed page count
stops seeing a push after about a day; the reach is set by the question's own moment instead, and the log's own end
(GitHub documents no retention limit, and keeps everything since this repository's first push on 11 Oct 2026)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from urllib.parse import parse_qsl, urlsplit

import requests

ACTIVITY_URL = "https://api.github.com/repos/{repository}/activity"
ACTIVITY_PARAMS = {"ref": "refs/heads/main", "per_page": 100}  # no time_period: the whole log, newest first
ACTIVITY_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
TIMEOUT_SECONDS = 30
PAGE_CAP = 2000  # a guard against a next link that never ends (200,000 pushes, about two years here), never a reach
ACCESS_REFUSED = (401, 403)


class ReceiptUnknown(RuntimeError):
    """GitHub's push time for the commit could not be established; the message says why."""


class ReceiptUnavailable(ReceiptUnknown):
    """The log could not be read (network, an HTTP error): no answer yet, worth asking again."""


class ReceiptAccessDenied(ReceiptUnavailable):
    """GitHub refused to show the activity log (HTTP 401 or 403): an access problem, not "no push yet"."""


class ActivityLog:
    def __init__(self, repository: str, token: str, get: Callable | None = None):
        self._repository, self._token, self._get = repository, token, get or requests.get
        self._pushes: list[dict] = []  # newest first, as GitHub pages them
        self._params: dict | None = dict(ACTIVITY_PARAMS)  # the next page's query; None once the log has ended
        self.pages = 0

    @property
    def ended(self) -> bool:
        return self._params is None

    @property
    def oldest(self) -> datetime | None:
        return _moment(self._pushes[-1]) if self._pushes else None

    def since(self, moment: datetime) -> list[dict]:
        """Every push at or after `moment`, oldest first, reading pages until one is older or the log ends."""
        while not self.ended and (self.oldest is None or self.oldest >= moment):
            self._read_page()
        return sorted((push for push in self._pushes if _moment(push) >= moment), key=_order)

    def _read_page(self) -> None:
        if self.pages >= PAGE_CAP:
            raise ReceiptUnavailable(f"GitHub's activity log ran past {PAGE_CAP} pages")
        response = self._page(ACTIVITY_URL.format(repository=self._repository), self._params)
        self.pages += 1
        self._pushes += response.json()
        following = response.links.get("next", {}).get("url")
        # GitHub's next link names the repository by numeric ID (`/repositories/<id>/`), which the cloud sessions'
        # GitHub proxy refuses (HTTP 403); the same page is asked by owner/name with its cursor
        self._params = {**ACTIVITY_PARAMS, **dict(parse_qsl(urlsplit(following).query))} if following else None

    def _page(self, url: str, params: dict | None):
        headers = {**ACTIVITY_HEADERS, "Authorization": f"Bearer {self._token}"}
        try:
            response = self._get(url, params=params, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as error:
            raise ReceiptUnavailable(f"GitHub's activity log not reached ({type(error).__name__})") from None
        if response.status_code in ACCESS_REFUSED:
            raise ReceiptAccessDenied(f"access refused: HTTP {response.status_code} from GitHub's activity log")
        if not response.ok:
            raise ReceiptUnavailable(f"HTTP {response.status_code} from GitHub's activity log")
        return response


def _moment(push: dict) -> datetime:
    return datetime.fromisoformat(push["timestamp"])


def _order(push: dict) -> tuple[datetime, int]:
    """Push order: by time, then by GitHub's activity id for pushes in the same second (story receipt-same-second).
    The id rises with every entry (measured 23 Oct: strictly, across all 3,929 entries since 11 Oct); timestamps are
    whole seconds, so two pushes can share one."""
    return _moment(push), push.get("id", 0)
