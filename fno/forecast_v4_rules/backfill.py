"""The exploratory back-fill of v4's phase-1 forecasts (story G7; PROTOCOL_v4.md section 8: 2017-26 data is spent, so
every row is labelled `backfill_exploratory`). It ends before the first live day; re-running writes identical files
(back-filled rows carry no `made_at`). V1 rows before A16 has 20 live sessions are not written."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .baselines import NOT_STARTED
from .capture import DayForecasts
from .records import BACKFILL


def backfill_days(forecasts: DayForecasts, first_live: date | None) -> list[date]:
    """Every scored session with an earlier close (so a forecast has inputs), up to the last close, before the first
    live day."""
    days = forecasts.days
    return [d for d in days[1:] if first_live is None or d < first_live]


def backfill(forecasts: DayForecasts, days: list[date], write) -> int:
    """Writes every forecaster's rows for `days`; returns the rows added."""
    rows = defaultdict(list)
    for d in days:
        for key, row in forecasts.records(d, BACKFILL, "").items():
            if row.status != NOT_STARTED:
                rows[key].append(row)
    return sum(write(f, q, found) for (f, q), found in rows.items())
