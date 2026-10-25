"""Protocol v4's implied baselines (PROTOCOL_v4.md section 3.1; story G7b completion, part b): raw implied
`IV30^2 x calendar days / 365` over a horizon, and premium-adjusted implied, raw implied times the median of
`RV_h(t) / raw_h(t)` over the ratio window, refit on the first scored session of each month. The window's rule
(1 Jan 2024 on, resolved before the refit day, the latest 750, at least 500) is `eligibility.premium_ratio_window`,
called, never re-implemented. Pure: no I/O. A value that cannot be computed is missing, never filled."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date
from functools import cache
from typing import Protocol

from ..forecast_v4.eligibility import premium_ratio_window
from ..forecast_v4.terms import CALENDAR_DAYS_A_YEAR
from .baselines import MISSING, NOT_ELIGIBLE, Value, before
from .series import DayValue


@dataclass(frozen=True)
class IvPoint:
    """One day's 30-day ATM implied volatility, annualised as a fraction (0.138, not 13.8)."""

    value: float
    flagged: bool  # a single-expiry estimate: never a raw or premium-adjusted value (protocol 3.1)


@dataclass(frozen=True)
class HorizonRv:
    """`RV_h(t)`: the sum of `t+1..t+h`'s session variances, resolved at `t+h`'s close."""

    value: float
    resolved_on: date


def raw_implied(iv: float, calendar_days: int) -> float:
    return iv * iv * calendar_days / CALENDAR_DAYS_A_YEAR


def horizon_sums(rv: list[DayValue], horizon: int) -> dict[date, HorizonRv]:
    """Each session t's `RV_h(t)` from a regular-session `RV_s` series (one row per session, in order), for every t
    whose whole horizon is in the series."""
    days, values = [r.day for r in rv], [r.value for r in rv]
    return {days[i]: HorizonRv(sum(values[i + 1 : i + 1 + horizon]), days[i + horizon])
            for i in range(len(rv) - horizon)}  # fmt: skip


def first_session_of_month(d: date, sessions: list[date]) -> date:
    """The refit day of `d`: the first scored session of `d`'s month (as HAR, `baselines.Har.refit_day`)."""
    return next(s for s in sessions if (s.year, s.month) == (d.year, d.month))


class PremiumRatio:
    """The median `RV_h(t) / raw_h(t)` over the window at a refit day; `raw_h(t)` uses the EOD IV30 of t and the
    calendar days from t to its resolution session `t+h`. Flagged and missing IV30 days are never window points."""

    def __init__(self, eod_iv30: dict[date, IvPoint], outcomes: dict[date, HorizonRv]):
        self.ratios = {
            t: rv.value / raw
            for t, rv in outcomes.items()
            if (iv := eod_iv30.get(t)) is not None and not iv.flagged
            and (raw := raw_implied(iv.value, (rv.resolved_on - t).days)) > 0
        }  # fmt: skip
        self.resolved = {t: outcomes[t].resolved_on for t in self.ratios}
        self.at = cache(self._at)

    def _at(self, refit_day: date) -> float | None:
        window = self.window(refit_day)
        return None if window is None else statistics.median(self.ratios[t] for t in window)

    def window(self, refit_day: date) -> list[date] | None:
        """The window's points at a refit (None: fewer than 500)."""
        return premium_ratio_window(self.resolved.items(), refit_day)


class RatioAt(Protocol):
    def at(self, refit_day: date) -> float | None: ...


class ImpliedBaselines:
    """Raw and premium-adjusted implied for one horizon from a day's IV30 (the pack's live, the EOD proxy in the
    back-fill) and the scored sessions; the horizon end `d+h` is the h-th scored session after `d`. `ratio`: the
    in-memory `PremiumRatio` (back-fill) or the month's stored one (`ratio_store.StoredRatio`, live)."""

    def __init__(self, horizon: int, sessions: list[date], ratio: RatioAt):
        self.h, self.sessions, self.ratio = horizon, sessions, ratio

    def raw(self, d: date, iv: IvPoint | None) -> Value:
        end = before(self.sessions, d) + (d in self.sessions) + self.h - 1
        if iv is None or iv.flagged or end >= len(self.sessions):
            return Value(MISSING)  # no IV30, a flagged one, or a horizon past the calendar
        return Value.of(raw_implied(iv.value, (self.sessions[end] - d).days))

    def premium_adjusted(self, d: date, iv: IvPoint | None) -> Value:
        raw = self.raw(d, iv)
        if raw.value is None:
            return raw
        ratio = self.ratio.at(first_session_of_month(d, self.sessions))
        return Value(NOT_ELIGIBLE) if ratio is None else Value.of(raw.value * ratio)
