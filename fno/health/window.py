"""The window, defined once (story O8): the NSE sessions dated from `days` calendar days before the run's IST date up to
that date. With 6 days, the oldest push a run can need (a 15:13 push on the first day, read at 23:59 on the last) is
6 days 8 h 47 min old, and session D is checked by every run from D to D + 6. GitHub's activity log keeps every push
(no `time_period`); the receipt search reads back to each commit's own date (story receipts-reach), so the window
only sets how many pages a run reads (about 3 a day here)."""

from __future__ import annotations

from datetime import date, timedelta

from ..research_data.calendar import SessionCalendar


def window_sessions(calendar: SessionCalendar, run_day: date, days: int) -> list[date]:
    return calendar.sessions(run_day - timedelta(days=days), run_day)


def window_days(run_day: date, days: int) -> list[date]:
    """Every calendar day of the window before the run's own day (the watcher's days)."""
    return [run_day - timedelta(days=back) for back in range(days, 0, -1)]
