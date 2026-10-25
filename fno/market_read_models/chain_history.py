"""The option chain's history blocks (story P9, W13's contract): daily NIFTY and India VIX closes and each expiry's
put-call ratio since the history's first day, and every in-scope contract's daily close (null on a day without trades)
and open interest, each history-dependent figure with its coverage: a value only when the days cover the period."""

from __future__ import annotations

from datetime import date
from statistics import median

from .chain_expiries import CALL, PUT, FoRow, contract_code

SPANS = {"d5": 5, "m1": 21, "m3": 63}  # screen 32's chart periods, in sessions
VIX_MIDDLE_SESSIONS = 63


def covered_change(series: list[float], span: int) -> dict:
    """The change over `span` sessions: needs span + 1 closes."""
    complete = len(series) > span
    value = round((series[-1] / series[-1 - span] - 1) * 100, 2) if complete else None
    return {"days_in_period": span, "days": max(min(len(series) - 1, span), 0), "complete": complete, "value": value}


def covered_middle(series: list[float], span: int) -> dict:
    """The median of the last `span` closes: needs span closes."""
    complete = len(series) >= span
    value = round(median(series[-span:]), 2) if complete else None
    return {"days_in_period": span, "days": min(len(series), span), "complete": complete, "value": value}


def chain_history(
    dates: list[date], nifty: list[float], vix: list[float], rows: list[FoRow], expiries: list[date]
) -> dict:
    """The ChainHistory payload: the index series and each of the session's expiries' daily put-call ratio."""
    totals: dict[tuple[date, date], dict[str, int]] = {}
    for r in rows:
        if r.kind in (CALL, PUT):
            totals.setdefault((r.expiry, r.day), {CALL: 0, PUT: 0})[r.kind] += r.oi
    pcr = {e.isoformat(): [_ratio(totals.get((e, d))) for d in dates] for e in expiries}
    coverage = {"nifty": {k: covered_change(nifty, n) for k, n in SPANS.items()},
                "vix_middle_3m": covered_middle(vix, VIX_MIDDLE_SESSIONS)}  # fmt: skip
    return {"dates": [d.isoformat() for d in dates], "nifty": nifty, "vix": vix, "pcr": pcr, "coverage": coverage}


def _ratio(total: dict[str, int] | None) -> float | None:
    return round(total[PUT] / total[CALL], 2) if total and total[CALL] else None


def contract_histories(rows: list[FoRow], monthly: set[date]) -> dict[str, dict]:
    """Code -> its ContractHistory payload, for every option among the rows: its own sessions, oldest first."""
    series: dict[str, list[FoRow]] = {}
    for r in rows:
        if r.kind in (CALL, PUT):
            series.setdefault(contract_code(r.expiry, r.strike, r.kind, r.expiry in monthly), []).append(r)
    return {code: _contract(code, sorted(days, key=lambda r: r.day)) for code, days in series.items()}


def _contract(code: str, days: list[FoRow]) -> dict:
    sessions = len(days)
    periods = {k: {"days_in_period": n, "days": min(sessions, n), "complete": sessions >= n} for k, n in SPANS.items()}
    return {
        "code": code, "dates": [r.day.isoformat() for r in days],
        "close": [r.close if r.volume > 0 else None for r in days],  # a close without trades is not a price
        "oi": [r.oi for r in days],
        "periods": {**periods, "life": {"days_in_period": None, "days": sessions, "complete": True}},
    }  # fmt: skip
