"""Experiment 1's monthly cycles (story B2, protocol section 3): one opportunity per NIFTY monthly expiry.

Decision day: the first trading day on which a monthly expiry (one with a NIFTY future listed that day,
`monthly_from_futures`) is 30-45 calendar days away. Entry: the next trading day. Exit: the last trading day with 21
or more calendar days to expiry.
Trading days come from NSE's session calendar (story A1), never from weekdays; Diwali's one-hour muhurat session is
not a trading day here (its closes are not normal daily closes, research/data/nifty-panel/README.md), so no cycle
decides, enters or exits on it. Only sessions with listed contracts count: a session the panel left out, or a
closes-only warm-up session (story A10), cannot be a decision day. A cycle is returned only when the panel covers its
whole window: its 30-45 day window opens on or after the first session with listed contracts (else its true decision
day is unknown) and its exit is on or before the last.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from ..constants import SESSION_MUHURAT
from ..research_data.calendar import SessionCalendar
from ..research_data.expiries import DAYS_TO_EXPIRY, monthly_from_futures
from ..research_data.panel_reader import NiftyPanel

EXIT_MIN_DAYS = 21  # exit: the last trading day with at least this many calendar days to expiry

ExpiryRule = Callable[[NiftyPanel], dict[date, set[date]]]  # the panel -> the monthly expiries known on each day


@dataclass(frozen=True)
class Cycle:
    expiry: date
    decision_day: date
    entry_day: date
    exit_day: date

    @property
    def has_entry_window(self) -> bool:
        """Protocol section 3: an entry day not before the exit day leaves no holding period (`no_entry_window`)."""
        return self.entry_day < self.exit_day


def cycle_rows(day: date, expiry: date) -> bool:
    """`keep` for `read_nifty_panel`: the option rows the simulator uses (21 or more days to expiry)."""
    return (expiry - day).days >= EXIT_MIN_DAYS


def futures_monthly(panel: NiftyPanel) -> dict[date, set[date]]:
    """The panel's monthly expiries on each day, from its listed futures."""
    return monthly_from_futures({day: (q.expiry for q in quotes) for day, quotes in panel.futures.items()})


class TradingDays:
    """The session calendar's sessions without muhurat sessions."""

    def __init__(self, calendar: SessionCalendar):
        self.calendar = calendar

    def is_trading_day(self, day: date) -> bool:
        kind = self.calendar.session_kind(day)
        return kind is not None and kind != SESSION_MUHURAT

    def next_after(self, day: date) -> date:
        day += timedelta(days=1)
        while not self.is_trading_day(day):
            day += timedelta(days=1)
        return day

    def last_on_or_before(self, day: date) -> date:
        while not self.is_trading_day(day):
            day -= timedelta(days=1)
        return day


def monthly_cycles(
    panel: NiftyPanel, calendar: SessionCalendar, expiry_rule: ExpiryRule = futures_monthly
) -> list[Cycle]:
    """Every complete cycle of the panel, in decision-day order."""
    days = TradingDays(calendar)
    monthly = expiry_rule(panel)
    data_days = [  # warm-up sessions (closes only, story A10) and left-out sessions list no contracts
        s.day for s in panel.sessions if s.underlying is not None and monthly.get(s.day) and days.is_trading_day(s.day)
    ]
    if not data_days:
        return []
    first_day, last_day = data_days[0], data_days[-1]
    cycles, seen = [], set()
    for day in data_days:
        for expiry in sorted(monthly.get(day, ())):
            if expiry in seen or not DAYS_TO_EXPIRY[0] <= (expiry - day).days <= DAYS_TO_EXPIRY[1]:
                continue
            if expiry - timedelta(days=DAYS_TO_EXPIRY[1]) < first_day:
                continue  # the window opened before the panel: its first trading day is not known
            seen.add(expiry)
            exit_day = days.last_on_or_before(expiry - timedelta(days=EXIT_MIN_DAYS))
            if exit_day <= last_day:
                cycles.append(Cycle(expiry, day, days.next_after(day), exit_day))
    return cycles
