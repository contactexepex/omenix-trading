"""Where circular lists come from: one port, one adapter per publisher (NSE's circulars API, SEBI's circulars page).
Each answers a whole list or raises FeedFailed; a file is downloaded through the same feed."""

from __future__ import annotations

import html
import re
from abc import ABC, abstractmethod
from dataclasses import replace
from datetime import date, datetime

import requests

from .model import DEPARTMENT_SEPARATOR, NSE, SEBI, Circular, FeedFailed

NSE_URL = "https://www.nseindia.com/api/circulars?fromDate={since:%d-%m-%Y}&toDate={until:%d-%m-%Y}"
NSE_FIELDS = ("cirDate", "circDisplayNo", "circDepartment", "circCategory", "sub", "circFilelink")
SEBI_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0"
SEBI_ROW = re.compile(
    r"<td>([A-Z][a-z]{2} \d{2}, \d{4})</td>\s*<td><a href=\"(https://www\.sebi\.gov\.in/legal/circulars/[^\"]+)\"[^>]*"
    r"title=\"([^\"]*)\""
)
SEBI_NUMBER = re.compile(r"_(\d+)\.html$")
SEBI_DATA_ROW = "<tr role='row' class="  # each circular's row (the header row has no class)
TIMEOUT_SECONDS = 60


class CircularFeed(ABC):
    LATEST_PAGE_ONLY = False  # True: the feed shows only its latest items, so a long gap could skip some

    def __init__(self, session: requests.Session):
        self.session = session

    @abstractmethod
    def fetch(self, since: date, until: date) -> list[Circular]:
        """Every circular the publisher lists for the dates (SEBI: its latest page); FeedFailed if not read whole."""

    def download(self, circular: Circular) -> bytes:
        return self._get(circular.link).content

    def _get(self, url: str) -> requests.Response:
        try:
            response = self.session.get(url, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise FeedFailed(f"{url}: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise FeedFailed(f"{url}: HTTP {response.status_code}")
        return response


class NseCircularApi(CircularFeed):
    def fetch(self, since: date, until: date) -> list[Circular]:
        url = NSE_URL.format(since=since, until=until)
        try:
            items = self._get(url).json()["data"]
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise TypeError("data is not a list of circulars")
            return _merged([self._circular(item) for item in items])
        except (ValueError, KeyError, TypeError) as exc:  # not JSON, no list, an item without its fields
            raise FeedFailed(f"{url}: not NSE's circular list ({type(exc).__name__}: {exc})") from exc

    @staticmethod
    def _circular(item: dict) -> Circular:
        missing = [field for field in NSE_FIELDS if not isinstance(item.get(field), str)]
        if missing:
            raise KeyError(f"circular without {missing}")
        issued = datetime.strptime(item["cirDate"], "%Y%m%d").date()
        return Circular(NSE, item["circDisplayNo"], issued, item["circDepartment"], item["circCategory"],
                        item["sub"].strip(), item["circFilelink"])  # fmt: skip


def _merged(listed: list[Circular]) -> list[Circular]:
    """One circular per link: NSE lists a circular once per department it concerns (NSE/CMTR/76963 under Futures &
    Options and under Capital Market), so its departments are joined, in NSE's order, and none is lost."""
    merged: dict[str, Circular] = {}
    for circular in listed:
        known = merged.get(circular.link)
        if known is None:
            merged[circular.link] = circular
        elif circular.department not in known.departments:
            department = DEPARTMENT_SEPARATOR.join((*known.departments, circular.department))
            merged[circular.link] = replace(known, department=department)
    return list(merged.values())


class SebiCircularList(CircularFeed):
    LATEST_PAGE_ONLY = True  # the latest 25 circulars (back to 7 Sep 2026 on 16 Oct 2026)

    def fetch(self, since: date, until: date) -> list[Circular]:
        page = self._get(SEBI_URL).text
        rows = SEBI_ROW.findall(page)
        if not rows:
            raise FeedFailed(f"{SEBI_URL}: no circular rows (the page's layout changed or it was not served)")
        if len(rows) != page.count(SEBI_DATA_ROW):  # a row whose layout changed would drop out unseen
            raise FeedFailed(f"{SEBI_URL}: {len(rows)} of {page.count(SEBI_DATA_ROW)} rows readable (layout changed)")
        return [self._circular(*row) for row in rows]

    @staticmethod
    def _circular(day: str, link: str, title: str) -> Circular:
        number = SEBI_NUMBER.search(link)
        if number is None:
            raise FeedFailed(f"{link}: no circular number in the link")
        issued = datetime.strptime(day, "%b %d, %Y").date()
        return Circular(SEBI, number.group(1), issued, "", "", html.unescape(title).strip(), link)
