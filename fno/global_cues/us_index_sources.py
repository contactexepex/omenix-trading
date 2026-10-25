"""Previous US index closes (story A17): S&P 500 from Cboe's delayed-quote history, Nasdaq 100 from Nasdaq's quote API.

Owner decision (row a927390 on main, 15 Oct 2026) after their terms were read and reported: use them for personal
research only, with raw files and values in the owner's Drive only (never in this public repository), at most one
download a day. Display (owner decision bcbbc454, 21 Oct 2026): the closes may be shown in the owner's Slack reports
and private dashboard, never in this public repository. Their terms, quoted in
`research/data/global-cues/README.md`, restrict automated capture (Nasdaq) and storing index values (Cboe); S&P Dow
Jones Indices owns the S&P 500, Nasdaq the Nasdaq 100.

Dates are New York trading dates; a close of date t is final at 16:00 US Eastern (01:30 IST on t+1 in US summer time,
02:30 IST in winter). On 15 Oct 2026 Cboe's file held 14 Oct's close at 00:09 UTC; Nasdaq's API had not added it at
00:30 UTC.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time

from .source import CueRequest, CueValue, GlobalCueSource, at_local, checked, positive

CBOE_SPX = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/_SPX.json"
NASDAQ_NDX = (
    "https://api.nasdaq.com/api/quote/NDX/historical?assetclass=index&fromdate={start}&todate={end}&limit={limit}"
)
NASDAQ_LIMIT = 10000  # rows per answer; an answer with fewer rows than its totalRecords is refused
US_EASTERN = "America/New_York"
US_CLOSE = time(16, 0)


def _json(data: bytes, what: str):
    try:
        return json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{what}: not the publisher's JSON (an error page?)") from exc


class UsIndexSource(GlobalCueSource):
    unit, date_zone, private, once_a_day, may_hold_unfinished = "index points", US_EASTERN, True, True, True
    max_age_days = 4  # Thursday's close on Monday (Good Friday), Friday's on Tuesday (a US Monday holiday)

    def available_at(self, value_date: date) -> datetime:
        return at_local(value_date, US_CLOSE, US_EASTERN)


class CboeSp500Source(UsIndexSource):
    cue, dataset = "sp500", "cboe/indices/spx-history"
    publisher = "Cboe Global Markets (delayed-quote history of SPX; S&P Dow Jones Indices owns the index)"

    def requests(self, start: date, end: date) -> list[CueRequest]:
        return [CueRequest("spx-history.json", CBOE_SPX)]  # the whole history in one file (about 1.7 MB)

    def parse(self, data: bytes) -> list[CueValue]:
        document = _json(data, self.cue)
        rows = document.get("data") if isinstance(document, dict) else None
        if not isinstance(rows, list):
            raise ValueError(f'{self.cue}: no "data" list')
        values = [CueValue(date.fromisoformat(r["date"]), positive(r["close"], r["date"], self.private)) for r in rows]
        return checked(values, self.cue)


class NasdaqNdxSource(UsIndexSource):
    cue, dataset = "nasdaq100", "nasdaq/indices/ndx-history"
    publisher = "Nasdaq, Inc. (owner of the Nasdaq-100 index), nasdaq.com quote API"
    holiday_rows = True  # 83 dates since 2007 that NYSE was closed, 82 repeating the previous close

    def requests(self, start: date, end: date) -> list[CueRequest]:
        url = NASDAQ_NDX.format(start=start.isoformat(), end=end.isoformat(), limit=NASDAQ_LIMIT)
        return [CueRequest(f"ndx-history_{start:%Y%m%d}_{end:%Y%m%d}.json", url)]

    def parse(self, data: bytes) -> list[CueValue]:
        document = _json(data, self.cue)
        table = ((document or {}).get("data") or {}).get("tradesTable") if isinstance(document, dict) else None
        rows = (table or {}).get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"{self.cue}: no tradesTable rows (Nasdaq's error answer?)")
        total = document["data"].get("totalRecords")
        if total != len(rows):
            raise ValueError(f"{self.cue}: {len(rows)} rows of {total}: the answer was cut")
        values = [
            CueValue(datetime.strptime(r["date"], "%m/%d/%Y").date(), positive(r["close"], r["date"], self.private))
            for r in rows
        ]
        return checked(values, self.cue)
