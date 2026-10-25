"""Which NIFTY expiry is the monthly one, decided as of each day from what NSE had listed by then (never from later
files). Research cycles use `monthly_from_futures` (story B2, 13 Oct 2026): `monthly_as_of`'s 50-day horizon was
measured on 2024-26 only and fails in 2019-2023, when NSE listed weeklies up to 69 days ahead. `monthly_as_of` stays
for the quote recorder (story A5); `monthly_expiries` (the last expiry of each month in one day's list) is the
descriptive flag stored by the capacity screen's fetch.py and the quote recorder's choice of contracts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date

DAYS_TO_EXPIRY = (30, 45)  # the agreed entry window, calendar days
MONTHLY_LISTING_DAYS = 50  # weeklies are never listed more than 42 days ahead (2024-26); every monthly was 60+ days


def monthly_expiries(listed: set[date]) -> set[date]:
    """The last listed expiry of each calendar month, from one day's complete list (weeklies included). A monthly
    expiry moved earlier for a holiday is still the month's last listed expiry."""
    last: dict[tuple[int, int], date] = {}
    for expiry in listed:
        key = (expiry.year, expiry.month)
        last[key] = max(expiry, last.get(key, expiry))
    return set(last.values())


def eligible_monthly(day: date, monthly: set[date]) -> date | None:
    """The nearest monthly expiry 30-45 calendar days away, or None (never a weekly substitute)."""
    window = [e for e in monthly if DAYS_TO_EXPIRY[0] <= (e - day).days <= DAYS_TO_EXPIRY[1]]
    return min(window) if window else None


def monthly_as_of(listings: dict[date, dict[date, int]]) -> dict[date, set[date]]:
    """Monthly expiries on each day: listed that day, and listed more than 50 days ahead on that day or before. Unlike
    "last expiry of the month", this is not fooled by a weekly moved into the month for a holiday (30 Apr 2025), and an
    old date dropped when NSE moved expiry day (25 Sep 2025 became 30 Sep 2025) no longer counts.
    `listings`: day -> {expiry: days to expiry that day}."""
    known: set[date] = set()
    out = {}
    for day in sorted(listings):
        known |= {e for e, dte in listings[day].items() if dte > MONTHLY_LISTING_DAYS}
        out[day] = {e for e in known if e in listings[day]}  # still listed: a re-dated contract drops its old date
    return out


def monthly_from_futures(future_expiries: Mapping[date, Iterable[date]]) -> dict[date, set[date]]:
    """Monthly expiries on each day: the expiries of the NIFTY futures listed that day. NSE lists index futures only on
    monthly contracts (near, next and far month), so no horizon is needed: a weekly, however far ahead it is listed or
    wherever a holiday moves it (30 Apr 2025), has no future, and a re-dated monthly (25 to 30 Sep 2025) moves with its
    future. Checked on every panel session 2019-2026: 3 futures a day, each with options of the same expiry."""
    return {day: set(expiries) for day, expiries in future_expiries.items()}
