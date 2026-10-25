"""The labelled end-of-day IV30 proxy `iv30_eod_close_proxy` (PROTOCOL_v4.md section 3.1; story G7b completion, part
b1): G1 v1's frozen estimator `PanelAtmIv30` on the A3 panel's first-archived end-of-day chains, one value per scored
session from 1 Jan 2024 (UDiFF files, outside G1's 2019-2023 holdout). Day t's chain is published on t's evening, so
a value is point in time for any later day's cutoff, never for t's own (the back-fill's close stands in for the pack,
protocol 1.6)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..forecast_v4.eligibility import PREMIUM_WINDOW_START
from .implied import IvPoint

PANEL_OPTION_DAYS = 100  # the panel rows kept in memory: IV30 reads only monthly expiries within about 95 days (G1)
POINTS_PER_UNIT = 100.0  # PanelAtmIv30 answers in volatility points (13.8), the baselines take a fraction (0.138)


def eod_iv30_series(days: list[date], estimate: Callable[[date], object | None]) -> dict[date, IvPoint]:
    """`estimate(day)` is `PanelAtmIv30.estimate` bound to the panel (an `AtmIv30` with `points` and `flagged`, or
    None). Days before 1 Jan 2024 and days without an estimate are left out (no value, never filled)."""
    found = {}
    for day in days:
        if day < PREMIUM_WINDOW_START:
            continue
        estimate_of_day = estimate(day)
        if estimate_of_day is not None:
            found[day] = IvPoint(estimate_of_day.points / POINTS_PER_UNIT, estimate_of_day.flagged)
    return found
