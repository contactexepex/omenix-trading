"""Each question's primary baseline series (protocol v4 3.2, `eligibility.primary_baseline`; story G8): V1 uses daily
HAR until intraday HAR is first eligible, then intraday HAR only (one way); every other question its one declared
baseline. A day without an eligible primary has no baseline value (the pair is missing, counted)."""

from __future__ import annotations

from datetime import date

from ...constants import V1_RV_1S, V4_BASELINE_HAR_DAILY, V4_BASELINE_HAR_INTRADAY
from ...forecast_v4.eligibility import primary_baseline
from ...forecast_v4.terms import PRIMARY_BASELINE
from .inputs import ForecastValue, V4ForecastSource

V1_CANDIDATES = (V4_BASELINE_HAR_DAILY, V4_BASELINE_HAR_INTRADAY)


def primary_names(question: str) -> frozenset[str]:
    return frozenset(V1_CANDIDATES) if question == V1_RV_1S else frozenset({PRIMARY_BASELINE[question]})


def primary_values(question: str, source: V4ForecastSource) -> dict[date, ForecastValue]:
    if question != V1_RV_1S:
        return source.values(question, PRIMARY_BASELINE[question])
    series = {name: source.values(question, name) for name in V1_CANDIDATES}
    chosen, intraday_started = {}, False
    for day in sorted(set().union(*series.values())):
        eligible = {name for name, values in series.items() if day in values and values[day].value is not None}
        name = primary_baseline(question, eligible, intraday_started)
        intraday_started = intraday_started or V4_BASELINE_HAR_INTRADAY in eligible
        chosen[day] = series[name][day] if name else ForecastValue(None, _live(series, day))
    return chosen


def _live(series: dict, day: date) -> bool:
    return any(values[day].live for values in series.values() if day in values)
