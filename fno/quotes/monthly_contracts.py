"""Which of today's listed expiries are monthly contracts, by A5's point-in-time rule (`monthly_as_of`, the one
definition research uses), never by "the last expiry of the month": that rule takes a weekly moved into the month for a
holiday (30 Apr 2025) as the monthly.

The rule needs history: an expiry is monthly when NSE listed it more than `MONTHLY_LISTING_DAYS` ahead on some day up
to today. An expiry further out than that today is monthly from today's list alone. For a nearer one, NSE's file of the
latest day at least `MONTHLY_LISTING_DAYS + 1` days before it is enough: a contract stays listed from its listing to
its expiry, so a monthly is in that file and a weekly (never listed more than 42 days ahead) is not.
"""

from __future__ import annotations

from datetime import date, timedelta

from ..research_data.expiries import MONTHLY_LISTING_DAYS, monthly_as_of
from .expiry_listing import ExpiryHistory


class PointInTimeMonthlies:
    def __init__(self, history: ExpiryHistory):
        self.history = history
        self._files: dict[tuple[str, date], tuple[date, list[date], dict]] = {}  # past files never change

    def monthlies(self, underlying: str, listed: list[date], today: date) -> tuple[set[date], list[dict]]:
        """Today's listed expiries that are monthly, and the provenance of every earlier file the answer used.
        Raises when an earlier file cannot be read (the caller records the failure; it never guesses)."""
        days_ahead = {e: (e - today).days for e in listed if e >= today}
        listings = {today: days_ahead}
        sources = []
        for expiry in sorted(e for e, days in days_ahead.items() if days <= MONTHLY_LISTING_DAYS):
            file_day, expiries, provenance = self._listed_on(underlying, expiry - timedelta(MONTHLY_LISTING_DAYS + 1))
            listings[file_day] = {e: (e - file_day).days for e in expiries}
            sources += [] if provenance in sources else [provenance]
        return monthly_as_of(listings)[today], sources

    def _listed_on(self, underlying: str, day: date) -> tuple[date, list[date], dict]:
        if (underlying, day) not in self._files:
            self._files[underlying, day] = self.history.listed_on(underlying, day)
        return self._files[underlying, day]
