"""G13b's record (part A3): one JSON per (underlying, day, issue), its header and one checked row per (forecaster,
horizon). Encoded as G13's records are, so a rebuilt back-fill day is byte-identical."""

from __future__ import annotations

import math

from ..price_distribution.records import encode
from .constants import (
    FORECASTERS,
    HORIZON_SESSIONS,
    HORIZONS_AT,
    LABELS,
    LEVELS,
    METHOD_VERSION,
    MISSING,
    NO_CHANGE,
    NOT_ELIGIBLE,
    OK,
)
from .forecasters import RangeForecast

__all__ = ["RecordRefused", "check_header", "check_row", "encode", "level_key", "range_row"]
BAD_ROW = "range row refused: {why}"


class RecordRefused(ValueError):
    """A row that breaks the record's rules is never written."""


def level_key(level: float, prefix: str) -> str:
    return f"{prefix}{round(level * 100):02d}"


def _round(value, digits: int):
    return None if value is None else round(value, digits)


def range_row(forecaster: str, horizon: str, target_day, tau: float | None, s_ref: float | None,
              forecast: RangeForecast) -> dict:  # fmt: skip
    row = {"forecaster": forecaster, "horizon": horizon, "target_day": target_day.isoformat() if target_day else None,
           "tau": _round(tau, 6), "s_ref": _round(s_ref, 2), "status": forecast.status, "reason": forecast.reason,
           "p_up": _round(forecast.p_up, 6), "p_big_move": _round(forecast.p_big_move, 6),
           "method_version": METHOD_VERSION}  # fmt: skip
    values = forecast.log_quantiles or (None,) * len(LEVELS)
    for level, value in zip(LEVELS, values, strict=True):
        row[level_key(level, "lq")] = _round(value, 8)
        row[level_key(level, "q")] = None if value is None or s_ref is None else round(s_ref * math.exp(value), 2)
    check_row(row)
    return row


def check_header(issue: str, label: str) -> None:
    """Every record, its rows and a missing record alike: an issue this version builds and a known label."""
    if issue not in HORIZONS_AT or label not in LABELS:
        raise RecordRefused(BAD_ROW.format(why=f"issue {issue!r} not built or label {label!r} unknown"))


def check_row(row: dict) -> None:
    why = None
    values = [row[level_key(level, "lq")] for level in LEVELS]
    if row["forecaster"] not in FORECASTERS or row["horizon"] not in HORIZON_SESSIONS:
        why = f"unknown forecaster or horizon {row['forecaster']}/{row['horizon']}"
    elif row["status"] not in (OK, MISSING, NOT_ELIGIBLE):
        why = f"unknown status {row['status']}"
    elif row["status"] == OK:
        pairs = list(zip(values, values[1:], strict=False))
        if any(v is None for v in values):
            why = "an ok row needs every quantile"
        elif row["forecaster"] == NO_CHANGE and any(b != a for a, b in pairs):
            why = "no_change is a point mass: its quantiles are equal"
        elif row["forecaster"] != NO_CHANGE and any(b <= a for a, b in pairs):
            why = "an ok row needs strictly increasing quantiles"
        elif row["p_up"] is None or not 0 <= row["p_up"] <= 1:
            why = "an ok row needs P(up) in [0, 1]"
    elif not row["reason"]:
        why = "a row that is not ok needs its reason"
    if why:
        raise RecordRefused(BAD_ROW.format(why=why))
