"""The option chain's per-contract figures (story P9, W13's contract): IV by Black-Scholes from the day's close, only
when the contract traded, Greeks from the same model, and the risk-neutral chance of ending beyond the break-even.
Prices and Greeks are the F&O tool's own (fno/analytics.py, story B1); the IV is searched only between 1% and 200%
a year (W13's examples, design/mockups/_platform/chain_data.py): a close no volatility in that range explains is not
a usable price, so it has no IV, Greeks or chance."""

from __future__ import annotations

from math import log, sqrt

from ..analytics import bs_greeks, bs_price, norm_cdf

IV_LOW, IV_HIGH = 0.01, 2.0
IV_STEPS = 80  # bisection steps: far below the 0.1-point rounding of the published IV


def years_to(days: int) -> float:
    return max(days, 0.25) / 365


def bounded_iv(price: float, spot: float, strike: float, years: float, rate: float, kind: str) -> float | None:
    """The volatility in [1%, 200%] whose Black-Scholes price is the close; None when none is."""
    low, high = IV_LOW, IV_HIGH
    if not bs_price(spot, strike, years, rate, low, kind) <= price <= bs_price(spot, strike, years, rate, high, kind):
        return None
    for _ in range(IV_STEPS):
        middle = (low + high) / 2
        low, high = (middle, high) if bs_price(spot, strike, years, rate, middle, kind) < price else (low, middle)
    return (low + high) / 2


def rounded_greeks(spot: float, strike: float, years: float, rate: float, iv: float, kind: str) -> dict:
    g = bs_greeks(spot, strike, years, rate, iv, kind)
    return {
        "delta": round(g.delta, 2), "gamma": round(g.gamma, 5), "theta": round(g.theta, 2), "vega": round(g.vega, 2),
    }  # fmt: skip


def chance_beyond(spot: float, breakeven: float, years: float, rate: float, iv: float, kind: str) -> int:
    """Percent: N(d2) that NIFTY ends above the break-even (a call), or below it (a put); risk-neutral."""
    above = norm_cdf((log(spot / breakeven) + (rate - iv * iv / 2) * years) / (iv * sqrt(years)))
    return round((above if kind == "CE" else 1 - above) * 100)
