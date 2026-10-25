"""Pricing, Greeks and option-chain statistics."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import OptionChain

SQRT2 = math.sqrt(2.0)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / SQRT2))


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def bs_price(spot: float, strike: float, t: float, r: float, sigma: float, kind: str) -> float:
    if t <= 0 or sigma <= 0:
        intrinsic = spot - strike if kind == "CE" else strike - spot
        return max(intrinsic, 0.0)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if kind == "CE":
        return spot * norm_cdf(d1) - strike * math.exp(-r * t) * norm_cdf(d2)
    return strike * math.exp(-r * t) * norm_cdf(-d2) - spot * norm_cdf(-d1)


@dataclass
class Greeks:
    delta: float
    gamma: float
    theta: float  # per calendar day
    vega: float  # per 1 vol point


def bs_greeks(spot: float, strike: float, t: float, r: float, sigma: float, kind: str) -> Greeks:
    t = max(t, 1e-6)
    sigma = max(sigma, 1e-4)
    sqrt_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma**2) * t) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    gamma = norm_pdf(d1) / (spot * sigma * sqrt_t)
    vega = spot * norm_pdf(d1) * sqrt_t / 100
    common = -spot * norm_pdf(d1) * sigma / (2 * sqrt_t)
    if kind == "CE":
        delta = norm_cdf(d1)
        theta = common - r * strike * math.exp(-r * t) * norm_cdf(d2)
    else:
        delta = norm_cdf(d1) - 1
        theta = common + r * strike * math.exp(-r * t) * norm_cdf(-d2)
    return Greeks(delta=delta, gamma=gamma, theta=theta / 365, vega=vega)


def implied_vol(price: float, spot: float, strike: float, t: float, r: float, kind: str) -> float | None:
    """Bisection IV solver; returns annualised vol as a fraction, or None."""
    intrinsic = max(spot - strike, 0) if kind == "CE" else max(strike - spot, 0)
    if price <= intrinsic or t <= 0:
        return None
    lo, hi = 1e-4, 5.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if bs_price(spot, strike, t, r, mid, kind) > price:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-6:
            break
    return (lo + hi) / 2


# ---------------------------------------------------------------- chain stats


def put_call_ratio(chain: OptionChain) -> float | None:
    call_oi = sum(q.oi for (_, k), q in chain.quotes.items() if k == "CE")
    put_oi = sum(q.oi for (_, k), q in chain.quotes.items() if k == "PE")
    return put_oi / call_oi if call_oi else None


def max_pain(chain: OptionChain) -> float:
    """Strike at which total option-writer payout at expiry is smallest."""
    strikes = chain.strikes()
    best, best_pain = strikes[0], float("inf")
    for settle in strikes:
        pain = 0.0
        for (k, kind), q in chain.quotes.items():
            if kind == "CE":
                pain += max(settle - k, 0) * q.oi
            else:
                pain += max(k - settle, 0) * q.oi
        if pain < best_pain:
            best, best_pain = settle, pain
    return best


def straddle_expected_move(chain: OptionChain) -> float | None:
    """ATM straddle price: the market's rough estimate of the move by expiry."""
    k = chain.atm_strike()
    ce, pe = chain.get(k, "CE"), chain.get(k, "PE")
    if not ce or not pe or ce.mid <= 0 or pe.mid <= 0:
        return None
    return ce.mid + pe.mid
