"""Which NIFTY expiry is the monthly one, decided as of each day from what NSE had listed by then (never from later
files). `monthly_as_of` stays for the quote recorder (story A5); `monthly_expiries` (the last expiry of each month in
one day's list) is the descriptive flag stored by the capacity screen's fetch.py and the quote recorder's choice of
contracts."""

from __future__ import annotations

from datetime import date

MONTHLY_LISTING_DAYS = 50  # weeklies are never listed more than 42 days ahead (2024-26); every monthly was 60+ days


def monthly_expiries(listed: set[date]) -> set[date]:
    """The last listed expiry of each calendar month, from one day's complete list (weeklies included). A monthly
    expiry moved earlier for a holiday is still the month's last listed expiry."""
    last: dict[tuple[int, int], date] = {}
    for expiry in listed:
        key = (expiry.year, expiry.month)
        last[key] = max(expiry, last.get(key, expiry))
    return set(last.values())


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
