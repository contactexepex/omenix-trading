"""Where raw files originally come from (an exchange archive, a data vendor). Each source knows only its own
naming and transport; callers see one interface."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime

import requests

from ..constants import MONTH_CODES
from ..http_pacing import REFUSALS_BEFORE_PAUSE, SourceCoolingOff
from ..models import now_utc
from .retry_policy import (
    MAX_RETRY_AFTER_SECONDS,
    NOT_PUBLISHED,
    OK,
    REFUSED,
    RETRY_WAITS,
    TOO_MANY_REQUESTS,
    UNBUILDABLE,
    retry_after_seconds,
    verdict,
)

NOT_PUBLISHED_REASON = "not served (HTTP 404)"
COOLING_OFF_STOP = "{error}; {left} file(s) not read: run again after the pause"  # a pass over many files stops


class RawSourceUnavailable(RuntimeError):
    """The source could not be reached (after retries); try again later. Not the same as "no such file"."""

    def __init__(self, message: str, status: int | None = None, tries: int = 0):
        super().__init__(message)
        self.status, self.tries = status, tries


class RawFileRefused(RawSourceUnavailable):
    """The source refused this one file (403, or any status but 2xx, 404, 429 and 5xx): never retried; a caller may
    go on to the next file."""


class RawSourceCoolingOff(RawSourceUnavailable):
    """The host is paused after refusals (`fno/http_pacing.py`, 15 minutes): every file would fail the same way, so a
    pass over many files stops here instead of listing each one."""


@dataclass(frozen=True)
class PublishedFile:
    data: bytes
    last_modified: datetime | None  # when the source last wrote the file, if it says (an upper bound on today's bytes)


class RawFileSource(ABC):
    name: str = "source"
    dataset: str = ""  # archive folder of this source's files: "<publisher>/<market>/<dataset>"
    first_day: date | None = None  # first day the archive keeps files for (None: not dated)
    last_day: date | None = None  # last day it publishes them for (None: still publishing)

    @abstractmethod
    def fetch(self, path: str) -> bytes | None:
        """The file at an archive path; None when the source does not publish it; RawSourceUnavailable on a failure."""

    def fetch_published(self, path: str) -> PublishedFile | None:
        """The file and when the source last wrote it; sources that cannot say report None for the time."""
        data = self.fetch(path)
        return None if data is None else PublishedFile(data, None)

    def last_written(self, path: str) -> datetime | None:
        """When the source last wrote the file (None if it has none or does not say); sources may answer cheaper."""
        found = self.fetch_published(path)
        return found.last_modified if found else None

    @staticmethod
    def dated_path(dataset: str, day: date, filename: str) -> str:
        """`<dataset>/<YYYY>/<MM>/<original file name>`: one folder per month, original names kept."""
        return f"{dataset}/{day:%Y}/{day:%m}/{filename}"


class NseArchiveSource(RawFileSource):
    """A dated file from NSE's public archive, through a polite session, under one retry policy (`retry_policy.py`,
    story A9b). A day without a file (holiday, weekend) is None; every failure is `RawSourceUnavailable` (a refused
    file: `RawFileRefused`), never an HTTP error. Subclasses give only the dataset, file name and URL."""

    name = "NSE archive"
    FILENAME = ""  # format string of the original file name for a day
    TIMEOUT_SECONDS = 60

    def __init__(self, session: requests.Session, sleep=time.sleep, clock=lambda: now_utc()):
        """`clock`: the time an HTTP-date `Retry-After` is measured from."""
        self.session, self.sleep, self.clock = session, sleep, clock

    @classmethod
    def filename_for(cls, day: date) -> str:
        return cls.FILENAME.format(day=day, mon=MONTH_CODES[day.month - 1])

    @classmethod
    def day_for(cls, filename: str) -> date:
        """The day an original file name is for (the inverse of filename_for); ValueError for any other name."""
        pattern = re.sub(r"\{day:(%[^}]+)\}", r"\1", cls.FILENAME).replace("{mon}", "%b")
        return datetime.strptime(filename, pattern).date()

    @classmethod
    def path_for(cls, day: date) -> str:
        return cls.dated_path(cls.dataset, day, cls.filename_for(day))

    BASE_URL = ""  # NSE folder the files are served from

    @classmethod
    def url_for(cls, path: str) -> str:
        """NSE's URL for an archive path: the folder's URL and the original file name."""
        return cls.BASE_URL + path.rsplit("/", 1)[-1]

    @classmethod
    def day_for_path(cls, path: str) -> date:
        """The day an archive path is for (dated sources: from the file name)."""
        return cls.day_for(path.rsplit("/", 1)[-1])

    def fetch(self, path: str) -> bytes | None:
        response = self._response(path)
        return None if response is None else response.content

    def fetch_published(self, path: str) -> PublishedFile | None:
        response = self._response(path)
        return None if response is None else PublishedFile(response.content, self._stamp(response))

    def last_written(self, path: str) -> datetime | None:
        response = self._response(path, head=True)  # headers only: a sweep of every file stays light
        return None if response is None else self._stamp(response)

    @staticmethod
    def _stamp(response: requests.Response) -> datetime | None:
        """NSE's Last-Modified (HTTP dates are GMT); None when absent or unreadable, never an error."""
        try:
            stamp = parsedate_to_datetime(response.headers.get("Last-Modified") or "")
        except (TypeError, ValueError):
            return None
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)

    def _response(self, path: str, head: bool = False) -> requests.Response | None:
        send, too_many = (self.session.head if head else self.session.get), 0
        for tries, scheduled in enumerate((*RETRY_WAITS, None), start=1):
            try:
                response = send(self.url_for(path), timeout=self.TIMEOUT_SECONDS)
            except SourceCoolingOff as exc:  # the host is paused: waiting here would only wait into the pause
                raise RawSourceCoolingOff(f"{self.name}: {path}: {exc}", tries=tries - 1) from exc
            except UNBUILDABLE as exc:
                raise RawSourceUnavailable(f"{self.name}: {path}: {exc} (not sent)", tries=tries) from exc
            except requests.RequestException as exc:
                if scheduled is None:
                    raise RawSourceUnavailable(f"{self.name}: {path}: {exc} after {tries} tries", tries=tries) from exc
                self.sleep(scheduled)
                continue
            outcome = verdict(response.status_code)
            if outcome == OK:
                return response
            if outcome == NOT_PUBLISHED:
                return None
            if outcome == REFUSED:
                raise RawFileRefused(self._failed(path, response, tries), response.status_code, tries)
            too_many = too_many + 1 if response.status_code == TOO_MANY_REQUESTS else 0
            if too_many >= REFUSALS_BEFORE_PAUSE:  # the pacer has just paused the host: never wait into the pause
                raise RawSourceCoolingOff(self._failed(path, response, tries), response.status_code, tries)
            self.sleep(self._retry_wait(path, response, scheduled, tries))
        raise AssertionError("unreachable")

    def _retry_wait(self, path: str, response: requests.Response, scheduled: int | None, tries: int) -> float:
        """The wait before the next try; raises when there is none or NSE asks for more than the cap."""
        asked = retry_after_seconds(response.headers.get("Retry-After"), self.clock())
        if scheduled is None or (asked is not None and asked > MAX_RETRY_AFTER_SECONDS):
            raise RawSourceUnavailable(self._failed(path, response, tries), response.status_code, tries)
        return max(scheduled, asked or 0)

    def _failed(self, path: str, response: requests.Response, tries: int) -> str:
        asked = response.headers.get("Retry-After")
        after = f" (Retry-After {asked})" if asked else ""
        return (
            f"{self.name}: {path}: HTTP {response.status_code}{after} after {tries} {'try' if tries == 1 else 'tries'}"
        )


class NseDailyFoSource(NseArchiveSource):
    """NSE's daily F&O file in the UDiFF format, served for every date from 1 January 2024."""

    dataset = "nse/derivatives/fo-bhavcopy"
    first_day = date(2024, 1, 1)
    BASE_URL = "https://nsearchives.nseindia.com/content/fo/"
    FILENAME = "BhavCopy_NSE_FO_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"


class NseLegacyFoSource(NseArchiveSource):
    """NSE's daily F&O file in the older format (served up to 5 July 2024), e.g. fo02JAN2019bhav.csv.zip. Its URL
    holds the year and month, read back from the archive path."""

    dataset = "nse/derivatives/fo-bhavcopy-legacy"
    first_day, last_day = date(2019, 1, 1), date(2024, 7, 5)  # the research needs nothing older than 2019
    BASE_URL = "https://nsearchives.nseindia.com/content/historical/DERIVATIVES/"
    FILENAME = "fo{day:%d}{mon}{day:%Y}bhav.csv.zip"

    @classmethod
    def url_for(cls, path: str) -> str:
        filename = path.rsplit("/", 1)[-1]
        return f"{cls.BASE_URL}{filename[7:11]}/{filename[4:7]}/{filename}"


class NseIndexCloseSource(NseArchiveSource):
    """NSE's daily closing values of all its indices (NIFTY 50, NIFTY Bank, India VIX and the rest)."""

    dataset = "nse/indices/index-close"
    first_day = date(2017, 1, 1)  # 2017-18: warm-up closes for 2019 features (F2: 250 previous VIX closes; A10)
    BASE_URL = "https://nsearchives.nseindia.com/content/indices/"
    FILENAME = "ind_close_all_{day:%d%m%Y}.csv"


class ParticipantOiSource(NseArchiveSource):
    """NSE's daily participant-wise open interest (client, DII, FII, pro: long and short contracts per instrument
    group), e.g. fao_participant_oi_09102026.csv. Published after the close (story A8)."""

    dataset = "nse/derivatives/participant-oi"
    first_day = date(2019, 1, 1)
    BASE_URL = "https://nsearchives.nseindia.com/content/nsccl/"
    FILENAME = "fao_participant_oi_{day:%d%m%Y}.csv"


class ParticipantVolumeSource(NseArchiveSource):
    """NSE's daily participant-wise trading volume (client, DII, FII, pro: contracts bought and sold per instrument
    group), the sister file of participant OI in the same layout, e.g. fao_participant_vol_21102026.csv (story A23)."""

    dataset = "nse/derivatives/participant-volume"
    first_day = date(2019, 1, 1)
    BASE_URL = "https://nsearchives.nseindia.com/content/nsccl/"
    FILENAME = "fao_participant_vol_{day:%d%m%Y}.csv"


class FiiDerivativeStatsSource(NseArchiveSource):
    """NSE's daily FII derivatives statistics (Excel 97): FII buy, sell and end-of-day open interest in contracts and
    crores per instrument group (and per index from 2026), e.g. fii_stats_21-Oct-2026.xls (story A23)."""

    dataset = "nse/derivatives/fii-stats"
    first_day = date(2019, 1, 1)
    BASE_URL = "https://nsearchives.nseindia.com/content/fo/"
    FILENAME = "fii_stats_{day:%d-%b-%Y}.xls"


class NseEquityBhavcopySource(NseArchiveSource):
    """NSE's daily capital-market file in the UDiFF format (every listed security's open, high, low, close, volume;
    story P6), e.g. BhavCopy_NSE_CM_0_0_0_20261012_F_0000.csv.zip."""

    dataset = "nse/equities/cm-bhavcopy"
    first_day = date(2025, 10, 1)  # P6: a year and a week before 12 Oct 2026 (the screener's 1Y figures, RSI)
    BASE_URL = "https://nsearchives.nseindia.com/content/cm/"
    FILENAME = "BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"


class NseDeliverySource(NseArchiveSource):
    """NSE's daily security-wise file with delivery quantities and delivery % (story P6), e.g.
    sec_bhavdata_full_12102026.csv."""

    dataset = "nse/equities/security-delivery"
    first_day = date(2025, 10, 1)
    BASE_URL = "https://nsearchives.nseindia.com/products/content/"
    FILENAME = "sec_bhavdata_full_{day:%d%m%Y}.csv"


class NseSpanBodSource(NseArchiveSource):
    """NSE Clearing's beginning-of-day SPAN risk-parameter file of a session, e.g. nsccl.20261014.i1.zip, written the
    evening before (18:00-03:05 IST in 131 sampled files; story A14: the margins C2 needs). Kept from 2 Jan 2020, NSE's
    first file, for A14c's stress-factor recompute (owner, 15 Oct 2026: everything since 1 Jan 2020)."""

    dataset = "nse/derivatives/span-bod"
    first_day = date(2020, 1, 2)
    BASE_URL = "https://nsearchives.nseindia.com/archives/nsccl/span/"
    FILENAME = "nsccl.{day:%Y%m%d}.i1.zip"
