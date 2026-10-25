"""Brent and USD/INR cues (story A17).

- Brent: the US Energy Information Administration's daily Europe Brent spot price FOB (series RBRTE, from Thomson
  Reuters/LSEG per EIA), one web page with the whole history in weekly rows. EIA releases it **weekly** (the page of
  7 Oct 2026 ended on 6 Oct; next release 15 Oct), so a Brent value is never known by the next NSE open: every Brent
  row is `backfilled` under the table's rule. Dates are the assessment dates (London trading days).
- USD/INR: the reference rate (rupees per US dollar), computed by FBIL from about 13:00-13:30 IST market quotes and
  published by RBI. RBI's own archive (rbi.org.in) has every Indian business day from 2000 to 9 Jul 2018, one day
  (24 Jul 2018), and every day from 12 Apr 2022, nothing in between. FBIL's archive (fbil.org.in, from 10 Jul 2018)
  covers the hole but its public site trails by about a week (on 15 Oct 2026 it ended on 7 Oct). Both are kept as
  separate cues and compared.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta

import requests

from .source import TIMEOUT_SECONDS, CueRequest, CueValue, GlobalCueSource, at_local, checked, positive

EIA_BRENT = "https://www.eia.gov/dnav/pet/hist/RBRTED.htm"
EIA_TITLE = "Europe Brent Spot Price FOB"
EIA_WEEK = re.compile(r"<td class='B6'>&nbsp;&nbsp;(\d{4}) (\w{3})-\s?(\d{1,2}) to [^<]*</td>(.*?)</tr>", re.S)
EIA_CELL = re.compile(r"<td class='B3'>([^<]*)</td>")
WEEKDAYS = 5
RBI_ARCHIVE = "https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx"
RBI_HEADER = "USD (INR / 1 USD)"
RBI_ANY_ROW = re.compile(r"<tr><td height=\"20\"")  # every data row, whatever its cells
RBI_ROW = re.compile(r'<td height="20" >(\d\d/\d\d/\d{4})</td><td height="20" align="right">([^<]*)</td>')
RBI_FORM_FIELD = re.compile(r'name="(__[A-Z]+)"[^>]*value="([^"]*)"')
FBIL_RATES = "https://www.fbil.org.in/wasdm/refrates/fetchfiltered?fromDate={start}&toDate={end}&authenticated=false"
FBIL_USD = "INR / 1 USD"
IST = "Asia/Kolkata"
REFERENCE_RATE_OUT = time(13, 30)  # FBIL's display time: 13:30 IST until about 2025, 13:00 since (the later is used)
EIA_WORST_LAG = timedelta(days=10)  # assumption: a weekly release (US daytime) publishes a value within 10 days


class EiaBrentSource(GlobalCueSource):
    cue, dataset, unit, date_zone = "brent", "eia/petroleum/brent-spot-daily", "US dollars a barrel", "Europe/London"
    publisher = "US Energy Information Administration, Europe Brent Spot Price FOB (RBRTE), weekly release"
    max_age_days = 16  # released weekly, the newest value up to about 9 days old

    def requests(self, start: date, end: date) -> list[CueRequest]:
        return [CueRequest("RBRTED.htm", EIA_BRENT)]

    def available_at(self, value_date: date) -> datetime:
        """An assumption, not an observation: EIA's weekly release dates are not archived (`live` rows are exact)."""
        return at_local(value_date + EIA_WORST_LAG, time(23, 59), IST)

    def parse(self, data: bytes) -> list[CueValue]:
        page = data.decode("utf-8", errors="replace")
        if EIA_TITLE not in page:
            raise ValueError(f"{self.cue}: not EIA's Brent page")
        values = []
        for year, month, day, cells in EIA_WEEK.findall(page):
            monday = datetime.strptime(f"{year} {month} {day}", "%Y %b %d").date()
            weekdays = EIA_CELL.findall(cells)
            if len(weekdays) != WEEKDAYS:  # dates come from the cell's position: refuse a row that would shift them
                raise ValueError(f"{self.cue}: the week of {monday} has {len(weekdays)} cells, not {WEEKDAYS}")
            for offset, text in enumerate(weekdays):
                if text.replace("&nbsp;", "").strip():  # a blank weekday is a gap, never filled
                    values.append(CueValue(monday + timedelta(offset), positive(text, f"{monday + timedelta(offset)}")))
        return checked(values, self.cue)


class ReferenceRateSource(GlobalCueSource):
    """The USD/INR reference rate of a date is fixed and published at about 13:00-13:30 IST that day."""

    def available_at(self, value_date: date) -> datetime:
        return at_local(value_date, REFERENCE_RATE_OUT, IST)


class RbiUsdInrSource(ReferenceRateSource):
    cue, dataset, unit, date_zone = "usdinr_rbi", "rbi/currency/reference-rate", "rupees per US dollar", IST
    publisher = "Reserve Bank of India, reference rate archive (the FBIL reference rate)"
    first_value_date = date(2007, 1, 1)
    max_age_days = 5  # a Thursday rate on Tuesday, after a Friday and a Monday holiday

    def requests(self, start: date, end: date) -> list[CueRequest]:
        form = (("txtFromDate", f"{start:%d/%m/%Y}"), ("txtToDate", f"{end:%d/%m/%Y}"), ("chkUSD", "on"))
        return [CueRequest(f"reference-rate-usd_{start:%Y%m%d}_{end:%Y%m%d}.html", RBI_ARCHIVE, form)]

    def download(self, session: requests.Session, request: CueRequest) -> bytes:
        """RBI's archive is a form: read it for its hidden fields, then post the request's dates."""
        page = session.get(request.url, timeout=TIMEOUT_SECONDS)
        page.raise_for_status()
        hidden = dict(RBI_FORM_FIELD.findall(page.text))
        if "__VIEWSTATE" not in hidden:
            raise ValueError(f"{self.cue}: RBI's form has no __VIEWSTATE field: the form changed")
        form = {**hidden, **dict(request.form), "btnSubmit": "Submit"}
        response = session.post(request.url, data=form, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.content

    def parse(self, data: bytes) -> list[CueValue]:
        page = data.decode("utf-8", errors="replace")
        if RBI_HEADER not in page:
            raise ValueError(f"{self.cue}: no {RBI_HEADER} table (not RBI's answer)")
        matched, every_row = RBI_ROW.findall(page), RBI_ANY_ROW.findall(page)
        if len(matched) != len(every_row):
            raise ValueError(f"{self.cue}: {len(every_row)} rows but {len(matched)} readable: layout changed")
        rows = [(datetime.strptime(d, "%d/%m/%Y").date(), v) for d, v in matched]
        return checked([CueValue(day, positive(v, str(day))) for day, v in rows], self.cue)


class FbilUsdInrSource(ReferenceRateSource):
    cue, dataset, unit, date_zone = "usdinr_fbil", "fbil/currency/reference-rate", "rupees per US dollar", IST
    publisher = "Financial Benchmarks India Pvt Ltd (FBIL), reference rates (public site, about a week late)"
    first_value_date = date(2018, 7, 10)  # FBIL took over the reference rate from RBI
    max_age_days = 14  # its public site trails by about a week
    private = True  # FBIL does not authorise commercial use without permission: Drive only (owner, 15 Oct; A17d)

    def requests(self, start: date, end: date) -> list[CueRequest]:
        url = FBIL_RATES.format(start=start.isoformat(), end=end.isoformat())
        return [CueRequest(f"reference-rates_{start:%Y%m%d}_{end:%Y%m%d}.json", url)]

    def parse(self, data: bytes) -> list[CueValue]:
        try:
            rows = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{self.cue}: not FBIL's JSON") from exc
        if not isinstance(rows, list):
            raise ValueError(f"{self.cue}: not FBIL's list of rates (an error answer?)")
        usd = [r for r in rows if isinstance(r, dict) and r.get("subProdName") == FBIL_USD]
        if rows and not usd:
            raise ValueError(f"{self.cue}: {len(rows)} rates but none named {FBIL_USD!r}: layout changed?")
        return checked([_fbil_value(r) for r in usd], self.cue)


def _fbil_value(row: dict) -> CueValue:
    stamp = str(row.get("processRunDate"))
    try:
        day = date.fromisoformat(stamp[:10])
    except ValueError as exc:
        raise ValueError(f"usdinr_fbil: bad date {stamp!r}") from exc
    return CueValue(day, positive(row.get("rate"), stamp))
