"""Where filing files come from (story A12), behind `RawFileSource` like every other raw dataset.

- `NseFilingFileSource`: one filing's XBRL file from NSE's archive host, addressed by its archive path
  (`nse/equities/filings/<kind>/<SYMBOL>/<NSE's file name>`).
- `NseAnnouncementsSource`, `NseBoardMeetingsSource`: NSE's list of every company's announcements (or board-meeting
  notices) made public on one calendar day, from NSE's website JSON, filed as `<dataset>/<YYYY>/<MM>/<name>`.
"""

from __future__ import annotations

from datetime import date

from ..constants import FILING_ANNOUNCEMENTS, FILING_BOARD_MEETINGS, NSE_FILINGS_FOLDER
from ..storage.raw_source import NseArchiveSource

NSE_XBRL_FOLDER = "https://nsearchives.nseindia.com/corporate/xbrl/"
WEB_PAGE_STARTS = (b"<!doctype html", b"<html")
DAY_LIST_FIRST_DAY = date(2005, 1, 1)  # NSE answers these lists from 2005 (measured); the queue decides the order


class NseFilingFileSource(NseArchiveSource):
    """A filing's XBRL file; NSE serves every results and shareholding XBRL file from one folder. For some listed links
    NSE answers HTTP 200 with its web page "The file you are trying to access doesn't appear to exist" (measured on
    two Larsen & Toubro revisions, March 2025): that is "not published" (None), like a 404."""

    name = "NSE filings archive"
    dataset = NSE_FILINGS_FOLDER
    BASE_URL = NSE_XBRL_FOLDER

    def fetch(self, path: str) -> bytes | None:
        data = super().fetch(path)
        return None if data is not None and is_web_page(data) else data

    @classmethod
    def path_for(cls, day: date) -> str:
        raise ValueError("a filing file is addressed by its filing (Filing.path), not by a day")


class NseDayListSource(NseArchiveSource):
    """One calendar day's all-company list from NSE's website JSON (subclasses give the dataset, name and API)."""

    first_day = DAY_LIST_FIRST_DAY
    API = ""  # format string with {day} as DD-MM-YYYY

    @classmethod
    def url_for(cls, path: str) -> str:
        return cls.API.format(day=f"{cls.day_for_path(path):%d-%m-%Y}")


class NseAnnouncementsSource(NseDayListSource):
    dataset = f"{NSE_FILINGS_FOLDER}/{FILING_ANNOUNCEMENTS}"
    FILENAME = "announcements_{day:%Y%m%d}.json"
    API = "https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={day}&to_date={day}"


class NseBoardMeetingsSource(NseDayListSource):
    dataset = f"{NSE_FILINGS_FOLDER}/{FILING_BOARD_MEETINGS}"
    FILENAME = "board-meetings_{day:%Y%m%d}.json"
    API = "https://www.nseindia.com/api/corporate-board-meetings?index=equities&from_date={day}&to_date={day}"


def is_web_page(data: bytes) -> bool:
    return data.lstrip()[:20].lower().startswith(WEB_PAGE_STARTS)
