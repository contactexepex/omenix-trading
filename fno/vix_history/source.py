"""NSE's India VIX daily history, one raw file per calendar month (story A15).

NSE serves it as JSON from its website (`/api/historicalOR/vixhistory?from=DD-MM-YYYY&to=DD-MM-YYYY`). Facts checked on
14-15 Oct 2026 from this repository's cloud session:
- the first day it serves is 19 Jul 2010: every window from Nov 2007 to Jun 2010 answers `{"data":[]}`;
- one answer holds at most 70 rows and cuts the rest silently (Jul-Dec 2010 gave 19 Jul to 25 Oct), so a month
  (at most 23 sessions) is one request and an answer with 70 rows or more is refused as possibly cut;
- a window of about two years answers an HTML "Service Temporarily Unavailable" page with HTTP 200;
- the same month read twice gives byte-identical answers (a CDN copy), so a different SHA-256 later is a real rewrite.

A month's file has no name at NSE, so it is filed as `india-vix-history/<YYYY>/<MM>/india-vix_<YYYYMM>.json`; its
"day" is the month's first day. Only a month that has ended is ever fetched, so a file never grows after it is saved.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..storage.raw_source import NseArchiveSource

API = "https://www.nseindia.com/api/historicalOR/vixhistory?from={start:%d-%m-%Y}&to={end:%d-%m-%Y}"


def month_start(day: date) -> date:
    return day.replace(day=1)


def month_end(month: date) -> date:
    return next_month(month) - timedelta(days=1)


def next_month(month: date) -> date:
    return date(month.year + month.month // 12, month.month % 12 + 1, 1)


def months_between(first: date, last: date) -> list[date]:
    """The first day of every month from `first`'s month to `last`'s month, both included."""
    months, month = [], month_start(first)
    while month <= last:
        months.append(month)
        month = next_month(month)
    return months


def last_complete_month(today: date) -> date:
    """The latest month that has ended before `today` (a month is fetched only once it is over)."""
    return month_start(month_start(today) - timedelta(days=1))


class NseVixHistorySource(NseArchiveSource):
    """One calendar month of India VIX daily open, high, low and close from NSE's website."""

    dataset = "nse/indices/india-vix-history"
    first_day = date(2010, 7, 1)  # the month of the first day NSE serves (19 Jul 2010; probed back to Nov 2007)
    FILENAME = "india-vix_{day:%Y%m}.json"

    @classmethod
    def path_for(cls, day: date) -> str:
        return super().path_for(month_start(day))

    @classmethod
    def url_for(cls, path: str) -> str:
        month = cls.day_for_path(path)
        return API.format(start=month, end=month_end(month))
