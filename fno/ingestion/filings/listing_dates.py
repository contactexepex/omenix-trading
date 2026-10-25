"""Each company's date of listing on NSE, from NSE's list of listed companies (`EQUITY_L.csv`; story A12, judge 51
addendum 8): the half-year coverage counts a company only from the period it was listed by."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

SYMBOL, LISTED = "SYMBOL", "DATE OF LISTING"  # NSE's header has leading spaces on all but the first two columns
LISTING_DATE_FORMAT = "%d-%b-%Y"  # e.g. 06-OCT-2008


def read_listing_dates(data: bytes, filename: str) -> dict[str, date]:
    """Symbol -> date of listing; ValueError when the file lacks either column or a date does not parse."""
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    header = [name.strip() for name in rows[0]] if rows else []
    if SYMBOL not in header or LISTED not in header:
        raise ValueError(f"{filename}: needs the columns {SYMBOL!r} and {LISTED!r}")
    symbol, listed = header.index(SYMBOL), header.index(LISTED)
    return {r[symbol]: datetime.strptime(r[listed].strip(), LISTING_DATE_FORMAT).date() for r in rows[1:] if r}
