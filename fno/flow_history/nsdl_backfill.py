"""The one-time back-fill of NSDL's FPI daily investment (story A23, scope 5; owner, 21 Oct 2026, DESK_DECISIONS
195b3f0f). NSDL's terms prohibit redistribution; under the owner's personal-research rule (50a79a43) the data lives in
private Drive only, never in this repository or a public place, and is read politely: one form post per month, one at
a time, at least `GAP_SECONDS` apart, one retry per month; a month that fails twice is listed, never looped. Each
answer is kept write-once in Drive with its receipt and its rows go to the flow-history table at once, so a resumed
pass skips the months already done. No value is printed or committed."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date

import requests

from ..storage.data_store import DataStore
from ..storage.part_table import PartTable
from ..storage.receipts import ReceiptFolder
from .nsdl import MEASURES as MEASURES_OF_ROW
from .nsdl import TOTAL, BadAnswer, FpiMonth, read_fpi_month

URL = "https://www.fpi.nsdl.co.in/web/Reports/Archive.aspx"
FORM_FIELDS = ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION")
SUBMIT = "btnSubmit1"
TIMEOUT_SECONDS = 60
GAP_SECONDS = 10.0
TRIES_PER_MONTH = 2
RAW_FILE = "flows/nsdl/raw/{month:%Y-%m}.html"
DATASET = "nsdl/fpi/daily-trends"
PUBLICATION_UNKNOWN = "publication_time_unknown"  # NSDL serves no write time; history only (no daily read)
RATE_SERIES, RATE_MEASURE = "USD/INR", "rate"


class NsdlUnavailable(RuntimeError):
    """The form did not answer (network, HTTP status, a page without its form fields)."""


class NsdlArchiveForm:
    def __init__(self, session: requests.Session):
        self.session, self.fields = session, None

    def month(self, up_to: date) -> str:
        """The answer for "To Date" `up_to`: every reporting date from the 1st of its month."""
        self.fields = self.fields or self._fields()
        data = {**self.fields, "__EVENTTARGET": SUBMIT, "__EVENTARGUMENT": "", "hdnDate": f"{up_to:%d-%b-%Y}",
                "HdnValexceldata": "", "hdnFlag": ""}  # fmt: skip
        return self._call("post", data=data)

    def forget(self) -> None:
        """After a failure the next post starts from a fresh page (its form state may have expired)."""
        self.fields = None

    def _fields(self) -> dict[str, str]:
        page = self._call("get")
        found = {name: re.search(rf'id="{name}" value="([^"]*)"', page) for name in FORM_FIELDS}
        if not all(found.values()):
            raise NsdlUnavailable("the archive page has no form fields")
        return {name: match.group(1) for name, match in found.items()}

    def _call(self, method: str, **options) -> str:
        try:
            response = getattr(self.session, method)(URL, timeout=TIMEOUT_SECONDS, **options)
        except requests.RequestException as exc:
            raise NsdlUnavailable(type(exc).__name__) from None
        if response.status_code != 200:
            raise NsdlUnavailable(f"HTTP {response.status_code}")
        return response.text


@dataclass
class BackfillResult:
    saved: list[date] = field(default_factory=list)
    skipped: list[date] = field(default_factory=list)
    failed: dict[date, str] = field(default_factory=dict)
    empty: list[date] = field(default_factory=list)  # saved, but NSDL listed no reporting date
    rows: int = 0


class NsdlBackfill:
    def __init__(self, form: NsdlArchiveForm, store: DataStore, receipts: ReceiptFolder, table: PartTable,
                 next_session: Callable[[date], date], sleep=time.sleep, monotonic=time.monotonic):  # fmt: skip
        self.form, self.store, self.receipts, self.table = form, store, receipts, table
        self.next_session, self.sleep, self.monotonic = next_session, sleep, monotonic
        self._last: float | None = None

    def run(self, month_ends: Sequence[date]) -> BackfillResult:
        result = BackfillResult()
        for month_end in month_ends:
            if self._done(month_end):
                result.skipped.append(month_end)
                continue
            try:
                page, month = self._fetch(month_end)
            except (NsdlUnavailable, BadAnswer) as problem:
                result.failed[month_end] = str(problem)
                continue
            self.store.put(RAW_FILE.format(month=month_end), page.encode())
            rows = self._rows(month)
            self.table.write(month_end, rows)
            result.saved.append(month_end)
            result.rows += len(rows)
            if not month.rows:
                result.empty.append(month_end)
        return result

    def _done(self, month_end: date) -> bool:
        raw = f"{self.store.area}/{RAW_FILE.format(month=month_end)}"
        table_month = f"{self.store.area}/{self.table.table}/{month_end:%Y}/{month_end:%m}"
        return self.receipts.read(raw) is not None and bool(self.receipts.under(table_month))

    def _fetch(self, month_end: date) -> tuple[str, FpiMonth]:
        for attempt in range(1, TRIES_PER_MONTH + 1):
            self._pace()
            try:
                page = self.form.month(month_end)
                return page, read_fpi_month(page, month_end)
            except (NsdlUnavailable, BadAnswer):
                self.form.forget()
                if attempt == TRIES_PER_MONTH:
                    raise
        raise AssertionError("TRIES_PER_MONTH is at least 1")

    def _pace(self) -> None:
        now = self.monotonic()
        if self._last is not None and now - self._last < GAP_SECONDS:
            self.sleep(GAP_SECONDS - (now - self._last))
        self._last = self.monotonic()

    def _rows(self, month: FpiMonth) -> list[dict]:
        rows = [self._row(r.reporting_date, f"{r.category}:{r.route}" if r.route else TOTAL, measure, value)
                for r in month.rows for measure, value in zip(MEASURES_OF_ROW, r.values)]  # fmt: skip
        return rows + [self._row(day, RATE_SERIES, RATE_MEASURE, rate) for day, rate in month.usd_inr.items()]

    def _row(self, day: date, series: str, measure: str, value: float) -> dict:
        return {"session": day.isoformat(), "dataset": DATASET, "last_modified": "",
                "available_from": self.next_session(day).isoformat(), "rewritten": PUBLICATION_UNKNOWN,
                "series": series, "measure": measure, "value": repr(value)}  # fmt: skip
