"""Official Asian index closes (story A17e): the index owners' own files where they answer without a login.

- SSE Composite from China Securities Index (CSIndex), which calculates the SSE indexes: JSON by date range, history
  from 2019. CSIndex puts a row on the requested start date even when it is a holiday, copying the next session (seen
  on 2019-01-01 and 2026-10-01), so every request starts `FAKE_ROW_MARGIN` earlier and the collector keeps only the
  wanted dates: the fake row is always before them, and no value is ever judged by its equality to another.
- TAIEX from the Taiwan Stock Exchange's open-data API: the current month only (no history before the first run).
- Nikkei 225 from Nikkei Indexes' daily CSV: about three years (from 2023-01-04).

Values are private (Drive only, owner rule 50a79a43): an error never shows a level.
"""

from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, datetime, timedelta

from .markets import SHANGHAI, TAIPEI, TOKYO
from .source import CueRequest, CueValue, GlobalCueSource, checked, positive

CSINDEX = "https://www.csindex.com.cn/csindex-home/perf/index-perf?indexCode=000001&startDate={start}&endDate={end}"
FAKE_ROW_MARGIN = timedelta(days=10)
TWSE_TAIEX = "https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST"
ROC_YEAR_OFFSET = 1911  # TWSE dates are in the Republic of China calendar: 115 is 2026
NIKKEI_CSV = "https://indexes.nikkei.co.jp/nkave/historical/nikkei_stock_average_daily_en.csv"
NIKKEI_HEADER = ["Date of Data", "Close", "Open", "High", "Low"]
NIKKEI_DATE = re.compile(r"\d{4}/\d{2}/\d{2}")


class OfficialAsianSource(GlobalCueSource):
    unit, private = "index points", True
    market = TOKYO

    def available_at(self, value_date: date) -> datetime:
        return self.market.available_at(value_date)


class CsindexShanghaiSource(OfficialAsianSource):
    cue, dataset, date_zone = "sse_composite", "csindex/indices/000001-perf", SHANGHAI.zone
    publisher = "China Securities Index Co. (calculates the SSE Composite), index performance API"
    first_value_date, max_age_days, market = date(2019, 1, 1), 10, SHANGHAI  # 10: the October Golden Week

    def requests(self, start: date, end: date) -> list[CueRequest]:
        first = start - FAKE_ROW_MARGIN
        url = CSINDEX.format(start=f"{first:%Y%m%d}", end=f"{end:%Y%m%d}")
        return [CueRequest(f"000001-perf_{first:%Y%m%d}_{end:%Y%m%d}.json", url)]

    def parse(self, data: bytes) -> list[CueValue]:
        rows = _json(data, self.cue).get("data")
        if not isinstance(rows, list):
            raise ValueError(f'{self.cue}: no "data" list (CSIndex\'s error answer?)')
        return checked([_dated(r["tradeDate"], "%Y%m%d", r["close"]) for r in rows], self.cue)


class TwseTaiexSource(OfficialAsianSource):
    cue, dataset, date_zone = "taiex", "twse/indices/taiex-month", TAIPEI.zone
    publisher = "Taiwan Stock Exchange open data (government open-data platform), TAIEX daily, current month"
    first_value_date, max_age_days, market = date(2026, 10, 1), 10, TAIPEI  # one month only; 10: the Lunar New Year

    def requests(self, start: date, end: date) -> list[CueRequest]:
        return [CueRequest("taiex-month.json", TWSE_TAIEX)]

    def parse(self, data: bytes) -> list[CueValue]:
        rows = _json(data, self.cue)
        if not isinstance(rows, list):
            raise ValueError(f"{self.cue}: not TWSE's list of days")
        return checked([_roc_value(r) for r in rows], self.cue, allow_empty=True)  # a new month before its first day


class NikkeiSource(OfficialAsianSource):
    cue, dataset, date_zone = "nikkei225", "nikkei/indices/nikkei225-daily", TOKYO.zone
    publisher = "Nikkei Inc. (owner of the Nikkei 225), Nikkei Indexes daily CSV"
    first_value_date, max_age_days, market = date(2023, 1, 4), 7, TOKYO  # the file's own first date

    def requests(self, start: date, end: date) -> list[CueRequest]:
        return [CueRequest("nikkei_stock_average_daily_en.csv", NIKKEI_CSV)]

    def parse(self, data: bytes) -> list[CueValue]:
        rows = list(csv.reader(io.StringIO(data.decode("latin-1"))))  # the footer has one Shift-JIS character
        if not rows or rows[0] != NIKKEI_HEADER:
            raise ValueError(f"{self.cue}: not Nikkei's CSV (header)")
        dated = [r for r in rows[1:] if r and NIKKEI_DATE.fullmatch(r[0])]  # the copyright footer is skipped
        if any(len(r) != len(NIKKEI_HEADER) for r in dated):
            raise ValueError(f"{self.cue}: a dated row without its {len(NIKKEI_HEADER)} cells (a cut download?)")
        return checked([_dated(r[0], "%Y/%m/%d", r[1]) for r in dated], self.cue)


def _json(data: bytes, cue: str):
    try:
        return json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{cue}: not the publisher's JSON (an error page?)") from exc


def _dated(text: str, form: str, close) -> CueValue:
    try:
        day = datetime.strptime(str(text), form).date()
    except ValueError:
        raise ValueError(f"a date cell is not a date in the form {form}") from None  # its text may be a level
    return CueValue(day, positive(close, day.isoformat(), True))


def _roc_value(row: dict) -> CueValue:
    text = str(row["Date"])
    if not re.fullmatch(r"\d{7}", text):
        raise ValueError("taiex: a TWSE date that is not seven digits (layout changed)")  # its text may be a level
    day = date(int(text[:3]) + ROC_YEAR_OFFSET, int(text[3:5]), int(text[5:]))
    return CueValue(day, positive(row["ClosingIndex"], day.isoformat(), True))
