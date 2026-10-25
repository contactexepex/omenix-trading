"""The US Treasury 10-year par yield (story A17), from the Treasury's daily par yield curve, one CSV per year (1990 on).
Quotes are taken near 15:30 US Eastern on each New York trading date t and published that evening, i.e. by about
04:30 IST on t+1, before NSE opens at 09:15 IST. US Government work: public domain.

"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time

from .source import CueRequest, CueValue, GlobalCueSource, at_local, checked, positive

TREASURY_YEAR = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
    "?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"
)
TREASURY_TEN_YEAR = "10 Yr"
TREASURY_POSTED = time(18, 0)  # assumption (reasoning only): posted by the evening of the quote day, US Eastern
US_EASTERN = "America/New_York"


class TreasuryTenYearSource(GlobalCueSource):
    cue, dataset, unit, date_zone = "us10y", "us-treasury/rates/par-yield-curve", "percent a year", US_EASTERN
    publisher = "US Department of the Treasury, daily par yield curve rates (10 Yr)"
    max_age_days = 4  # as the US closes: a Thursday value on Monday, a Friday value on Tuesday

    def available_at(self, value_date: date) -> datetime:
        return at_local(value_date, TREASURY_POSTED, US_EASTERN)

    def requests(self, start: date, end: date) -> list[CueRequest]:
        years = range(start.year, end.year + 1)
        return [CueRequest(f"daily-treasury-rates_{year}.csv", TREASURY_YEAR.format(year=year)) for year in years]

    def parse(self, data: bytes) -> list[CueValue]:
        try:
            reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
            fields, rows = reader.fieldnames or [], list(reader)
        except UnicodeDecodeError as exc:
            raise ValueError(f"{self.cue}: not the Treasury's CSV") from exc
        if TREASURY_TEN_YEAR not in fields or "Date" not in fields:
            raise ValueError(f"{self.cue}: no Date and {TREASURY_TEN_YEAR} columns (not the Treasury's CSV)")
        dated = [r for r in rows if (r[TREASURY_TEN_YEAR] or "").strip()]  # a blank cell is a gap, never filled
        values = [CueValue(_us_date(r["Date"]), positive(r[TREASURY_TEN_YEAR], r["Date"])) for r in dated]
        return checked(values, self.cue, allow_empty=True)  # a new year's file is empty until its first day


def _us_date(text: str) -> date:
    return datetime.strptime(text, "%m/%d/%Y").date()
