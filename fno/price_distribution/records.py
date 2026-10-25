"""G13's day record as JSON (sections 2-4): the valuation, the forecast rows and the labels, encoded the same way
every time so a rebuilt back-fill day is byte-identical. Rows are checked before they are written."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from .constants import (
    AI_SLOTS,
    DISTRIBUTION_LEVELS,
    FORECAST_LEVELS,
    FORECASTERS,
    HORIZONS,
    LABELS,
    METHOD_VERSION,
    MISSING,
    NOT_ELIGIBLE,
    NOT_STARTED,
    OK,
    RISK_NEUTRAL_NOTE,
    SMILE_VALUE_NOTE,
)
from .forecasters import Forecast
from .horizons import Target
from .smile import ContractValue
from .valuation import DayValuation, ExpiryValuation

SCHEMA = "g13_day_v1"
RATE_SOURCE = "config.yaml risk_free_rate (labelled until A21's T-bill capture lands)"
DIGITS = 6
BAD_ROW = "forecast row refused: {why}"


class RecordRefused(ValueError):
    """A row that breaks the record's rules is never written."""


@dataclass(frozen=True)
class Stamp:
    """What every row of one build carries."""

    label: str
    method_sha256: str
    inputs_sha256: str
    made_at: str | None  # live only


def level_key(level: float, prefix: str) -> str:
    return f"{prefix}{round(level * 100):02d}"


def _round(value: float | None, digits: int = DIGITS) -> float | None:
    return None if value is None else round(value, digits)


def _points(value: float | None) -> float | None:
    return None if value is None else round(value * 100, 4)


def forecast_row(day, forecaster: str, target: Target, s_ref: float | None, forecast: Forecast, stamp: Stamp) -> dict:
    row = {"day": day.isoformat(), "forecaster": forecaster, "horizon": target.horizon,
           "target_day": target.day.isoformat() if target.day else None, "sessions": target.sessions,
           "s_ref": _round(s_ref, 2), "status": forecast.status, "reason": forecast.reason, "label": stamp.label,
           "tail_levels": list(forecast.tail_levels), "method_version": METHOD_VERSION,
           "method_sha256": stamp.method_sha256, "inputs_sha256": stamp.inputs_sha256,
           "made_at": stamp.made_at}  # fmt: skip
    values = forecast.log_quantiles or (None,) * len(FORECAST_LEVELS)
    for level, value in zip(FORECAST_LEVELS, values, strict=True):
        row[level_key(level, "lq")] = _round(value, 8)
        row[level_key(level, "q")] = None if value is None else round(s_ref * math.exp(value), 2)
    check_row(row)
    return row


def check_row(row: dict) -> None:
    why = None
    if row["forecaster"] not in FORECASTERS or row["horizon"] not in HORIZONS or row["label"] not in LABELS:
        why = f"unknown forecaster, horizon or label in {row['forecaster']}/{row['horizon']}/{row['label']}"
    elif row["status"] not in (OK, MISSING, NOT_ELIGIBLE, NOT_STARTED):
        why = f"unknown status {row['status']}"
    elif row["status"] == NOT_STARTED and row["forecaster"] not in AI_SLOTS:
        why = f"{NOT_STARTED} is for the AI books' slots only, not {row['forecaster']}"
    elif row["status"] == OK:
        values = [row[level_key(level, "lq")] for level in FORECAST_LEVELS]
        if any(v is None for v in values) or any(b <= a for a, b in zip(values, values[1:], strict=False)):
            why = "an ok row needs strictly increasing quantiles"
    elif not row["reason"]:
        why = "a row that is not ok needs its reason"
    if why:
        raise RecordRefused(BAD_ROW.format(why=why))


def contract_dict(c: ContractValue) -> dict:
    return {"contract_id": c.contract_id, "strike": c.strike, "kind": c.kind, "bid": c.bid, "ask": c.ask,
            "price": _round(c.price, 4), "iv_points": _points(c.iv), "delta": _round(c.delta, 4),
            "smile_iv_points": _points(c.smile_iv), "smile_value": _round(c.smile_value, 4),
            "smile_value_minus_price_rs": _round(c.gap_rs, 4), "smile_gap_iv_points": _round(c.gap_iv_points, 4),
            "smile_value_inside_spread": c.inside_spread}  # fmt: skip


def expiry_dict(e: ExpiryValuation) -> dict:
    out = {"expiry": e.expiry.isoformat(), "days": e.days, "status": e.status, "reason": e.reason,
           "quoted": e.quoted, "used": len(e.used.quotes) if e.used else 0,
           "dropped": e.used.dropped if e.used else {}, "forward": _round(e.forward, 4),
           "future_last": e.future,
           "forward_minus_future": _round(e.forward - e.future, 4) if e.forward and e.future else None}  # fmt: skip
    if e.surface is not None:
        s = e.surface
        out |= {"atm_strike": s.atm_strike, "atm_iv_points": _points(s.atm_iv),
                "delta_iv_points": {name: _points(v) for name, v in s.delta_ivs.items()},
                "risk_reversal_25_points": _points(s.risk_reversal_25), "butterfly_25_points": _points(s.butterfly_25),
                "otm_points": [{"strike": p.strike, "kind": p.kind, "iv_points": _points(p.iv),
                                "delta": _round(p.delta, 4)} for p in s.otm]}  # fmt: skip
    if e.distribution is not None:
        out["distribution"] = _distribution_dict(e)
    if e.status == OK:
        out |= {"smile": None if e.smile is None else {"coefficients": [_round(c, 8) for c in e.smile.coefficients],
                                                       "rmse_iv_points": _round(e.smile.rmse_points, 4)},
                "smile_reason": e.smile_reason, "contracts": [contract_dict(c) for c in e.contracts]}  # fmt: skip
    return out


def _tail_dict(tail) -> dict:
    return {"strike": tail.strike, "cdf": _round(tail.cdf), "iv_points": _points(tail.vol)}


def _quantile_dict(strike: float, source: str, forward: float) -> dict:
    return {"level": _round(strike, 2), "log_return": _round(math.log(strike / forward), 8), "source": source}


def _distribution_dict(e: ExpiryValuation) -> dict:
    found = e.distribution.distribution
    if found is None:
        return {"status": MISSING, "reason": e.distribution.reason}
    mean = found.mean()
    quantiles = {
        level_key(level, "q"): _quantile_dict(strike, source, found.forward)
        for level, (strike, source) in found.quantiles(DISTRIBUTION_LEVELS).items()
    }
    return {
        "status": OK,
        "raw_decreases": found.raw_decreases,
        "mean": _round(mean, 4),
        "mean_minus_forward_share": _round(mean / found.forward - 1, 8),
        "lower_tail": _tail_dict(found.lower),
        "upper_tail": _tail_dict(found.upper),
        "cdf": [[strike, _round(cdf)] for strike, cdf in found.points],
        "quantiles": quantiles,
        "note": RISK_NEUTRAL_NOTE,
    }


def valuation_dict(v: DayValuation, realised_points: float | None) -> dict:
    near = next((e for e in v.expiries if e.surface is not None and e.surface.atm_iv is not None), None)
    gap = near.surface.atm_iv * 100 - realised_points if near is not None and realised_points is not None else None
    iv30 = None if v.iv30 is None else {"points": _round(v.iv30.points, 4), "flagged": v.iv30.flagged,
                                        "expiries": [e.isoformat() for e in v.iv30.expiries]}  # fmt: skip
    return {
        "iv30": iv30,
        "rv20_points": _round(realised_points, 4),
        "near_atm_iv_minus_rv20_points": _round(gap, 4),
        "smile_value_note": SMILE_VALUE_NOTE,
        "expiries": [expiry_dict(e) for e in v.expiries],
    }


def encode(record: dict) -> bytes:
    return (json.dumps(record, sort_keys=True, indent=1, allow_nan=False) + "\n").encode()
