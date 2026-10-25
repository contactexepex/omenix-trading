"""Where a company's filings are listed (story A12): one `FilingIndex` per filing list of an exchange. Each knows only
its own JSON; callers get `Filing` records. A swap to another exchange (BSE) is one new class here plus one line in
`fno/filings/wiring.py`.

NSE lists results in two places: the classic results list holds every quarter up to December 2024; from the March
2025 quarter, results are filed as SEBI's "Integrated Filing - Financials" and listed only there (measured 13 Oct
2026, `reviews/claude/response_56_2026-10-13-a12-filings-archive.md`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date, datetime, timedelta

from ..constants import CONSOLIDATED, FILING_RESULTS, FILING_SHAREHOLDING, STANDALONE
from ..models import IST
from .filing import Filing

JsonGetter = Callable[[str, dict], object]  # (path on the exchange's website, query parameters) -> parsed JSON

NSE_LEGACY_RESULTS = "/api/corporates-financial-results"
NSE_INTEGRATED_RESULTS = "/api/integrated-filing-results"
NSE_SHAREHOLDING = "/api/corporate-share-holdings-master"
INTEGRATED_FINANCIALS = "Integrated Filing- Financials"  # NSE's type name (the governance filings are not numbers)
NSE_CONSOLIDATION = {"Consolidated": CONSOLIDATED, "Non-Consolidated": STANDALONE, "Standalone": STANDALONE}
OLDEST_LATE_FILING = timedelta(days=400)  # a period ending this long before the window cannot be filed inside it
MAX_PAGES = 20  # NSE pages the integrated list 20 per page; 3 years are about 3 pages


def nse_time(text: str | None) -> datetime | None:
    """NSE's '09-Jan-2025 21:39:43', '21-JUL-2026 15:44:00' or '21-Apr-2007 14:50' (month in any case) as IST; None
    when absent."""
    if not text or text.strip() in ("-", ""):
        return None
    text = text.strip()
    return datetime.strptime(text, "%d-%b-%Y %H:%M:%S" if text.count(":") == 2 else "%d-%b-%Y %H:%M").replace(
        tzinfo=IST
    )


def nse_day(text: str) -> date:
    return datetime.strptime(text.strip(), "%d-%b-%Y").date()


def public_time(*texts: str | None) -> datetime:
    """The later of NSE's times for one filing: from then on it was surely public (ValueError when none is given)."""
    times = [t for t in map(nse_time, texts) if t is not None]
    if not times:
        raise ValueError("NSE gives no time for this filing")
    return max(times)


def xbrl_link(value: str | None) -> str:
    """NSE's link to the XBRL file, or "" when the list has none (shown as '-', null, or a link ending in '/-')."""
    if not value or not value.startswith("http") or value.rsplit("/", 1)[-1] in ("", "-"):
        return ""
    return value


def _timed(row: dict) -> bool:
    """Whether a classic results row has NSE's broadcast or dissemination time (rows before about 2008 have only the
    filing date and minute)."""
    return bool(nse_time(row.get("broadCastDate")) or nse_time(row.get("exchdisstime")))


def _placeable(row: dict) -> bool:
    """Rows before about 2008 may have neither a time nor an XBRL file: nothing to archive and no moment to place
    them at, so they are left out (rows with an XBRL file always have a time; one without would fail loudly)."""
    return _timed(row) or bool(nse_time(row.get("filingDate"))) or bool(xbrl_link(row.get("xbrl")))


class FilingIndex(ABC):
    name: str = "index"
    kind: str = ""  # FILING_RESULTS or FILING_SHAREHOLDING

    def __init__(self, get_json: JsonGetter):
        self.get_json = get_json

    @abstractmethod
    def filings(self, symbol: str, since: date) -> list[Filing]:
        """The company's filings made public on or after `since`; a filing without an XBRL file has url ""."""


class NseLegacyResultsIndex(FilingIndex):
    """NSE's classic quarterly results list (every quarter up to December 2024)."""

    name, kind = "NSE results list", FILING_RESULTS
    MARKET, PERIOD_END = "equities", "toDate"  # NSE's list and the field holding the period's last day

    def filings(self, symbol: str, since: date) -> list[Filing]:
        params = {"index": self.MARKET, "symbol": symbol, "period": "Quarterly"}
        rows = self.get_json(NSE_LEGACY_RESULTS, params)
        oldest = since - OLDEST_LATE_FILING
        recent = [r for r in rows or [] if nse_day(r[self.PERIOD_END]) >= oldest and _placeable(r)]
        found = (self._filing(symbol, row) for row in recent)
        return [f for f in found if f.filed_at.date() >= since]

    def _filing(self, symbol: str, row: dict) -> Filing:
        return Filing(
            FILING_RESULTS,
            symbol,
            nse_day(row[self.PERIOD_END]),
            public_time(row.get("broadCastDate"), row.get("exchdisstime"))
            if _timed(row)
            else public_time(row.get("filingDate")),
            xbrl_link(row.get("xbrl")),
            NSE_CONSOLIDATION.get(row.get("consolidated"), ""),
        )


class NseInsuranceResultsIndex(NseLegacyResultsIndex):
    """NSE's classic results list for insurers (`index=insurance`): their results before the integrated filings are
    not in the equities list (LIC: 0 rows there; here the June to December 2024 quarters, measured 13 Oct 2026)."""

    name = "NSE insurance results list"
    MARKET, PERIOD_END = "insurance", "periodEnd"


class NseIntegratedResultsIndex(FilingIndex):
    """NSE's integrated filings list, financial results only (the March 2025 quarter onwards); paged."""

    name, kind = "NSE integrated filings list", FILING_RESULTS

    def filings(self, symbol: str, since: date) -> list[Filing]:
        rows = self._rows(symbol)
        found = (self._filing(symbol, row) for row in rows if row.get("type") == INTEGRATED_FINANCIALS)
        return [f for f in found if f.filed_at.date() >= since]

    def _rows(self, symbol: str) -> list[dict]:
        rows: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            answer = self.get_json(NSE_INTEGRATED_RESULTS, {"index": "equities", "symbol": symbol, "page": page})
            new = [r for r in answer.get("data") or [] if r not in rows]
            rows += new
            if not new or len(rows) >= int(answer.get("totalCount") or 0):
                return rows
        raise ValueError(f"{symbol}: NSE's integrated filings list has more than {MAX_PAGES} pages")

    def _filing(self, symbol: str, row: dict) -> Filing:
        return Filing(
            FILING_RESULTS,
            symbol,
            nse_day(row["qe_Date"]),
            public_time(row.get("broadcast_Date"), row.get("creation_Date")),
            xbrl_link(row.get("xbrl")),
            NSE_CONSOLIDATION.get(row.get("consolidated"), ""),
        )


class NseShareholdingIndex(FilingIndex):
    """NSE's shareholding-pattern list (quarterly). It shows a revised pattern in place of the original one."""

    name, kind = "NSE shareholding list", FILING_SHAREHOLDING

    def filings(self, symbol: str, since: date) -> list[Filing]:
        rows = self.get_json(NSE_SHAREHOLDING, {"index": "equities", "symbol": symbol})
        found = (self._filing(symbol, row) for row in rows or [])
        return [f for f in found if f.filed_at.date() >= since]

    def _filing(self, symbol: str, row: dict) -> Filing:
        return Filing(
            FILING_SHAREHOLDING,
            symbol,
            nse_day(row["date"]),
            public_time(row.get("broadcastDate"), row.get("systemDate")),
            xbrl_link(row.get("xbrl")),
        )
