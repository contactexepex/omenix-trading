"""C4's own option pricing (story C4, judge 83), written apart from B1's model. It uses Black-76 on the
same-expiry forward, with the rate only discounting. The forward comes from put-call parity at the strike where the
call and put mids are closest, so it needs no futures feed. Each leg's volatility is implied from its own mid by
bisection. Time is calendar days over 365; at expiry a leg is worth its intrinsic value."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

DAYS_PER_YEAR = 365.0
SIGMA_LOW, SIGMA_HIGH, BISECTIONS = 1e-4, 5.0, 100


class PricingProblem(ValueError):
    """A leg C4 cannot price from the snapshot: the trade fails closed."""


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def intrinsic(kind: str, forward: float, strike: float) -> float:
    return max(forward - strike, 0.0) if kind == "CE" else max(strike - forward, 0.0)


def black76(kind: str, forward: float, strike: float, years: float, rate: float, sigma: float) -> float:
    if years <= 0:
        return intrinsic(kind, forward, strike)
    spread = sigma * math.sqrt(years)
    d1 = (math.log(forward / strike) + spread * spread / 2) / spread
    d2 = d1 - spread
    discount = math.exp(-rate * years)
    if kind == "CE":
        return discount * (forward * _norm_cdf(d1) - strike * _norm_cdf(d2))
    return discount * (strike * _norm_cdf(-d2) - forward * _norm_cdf(-d1))


def implied_vol(price: float, kind: str, forward: float, strike: float, years: float, rate: float) -> float:
    if years <= 0:
        return 0.0  # on the expiry day a leg is valued at its intrinsic value: its volatility is never used
    low, high = SIGMA_LOW, SIGMA_HIGH

    def priced(sigma: float) -> float:
        return black76(kind, forward, strike, years, rate, sigma)

    if not priced(low) <= price <= priced(high):
        raise PricingProblem(f"no volatility gives {price:g} for the {strike:g} {kind}")
    for _ in range(BISECTIONS):
        middle = (low + high) / 2
        low, high = (middle, high) if priced(middle) < price else (low, middle)
    return (low + high) / 2


def parity_forward(calls: Mapping[float, float], puts: Mapping[float, float], years: float, rate: float) -> float:
    """F = K + e^(rT) (C - P) at the strike whose call and put mids are closest."""
    both = sorted(set(calls) & set(puts), key=lambda k: (abs(calls[k] - puts[k]), k))
    if not both:
        raise PricingProblem("no strike with both a call and a put quote: the forward cannot be found")
    strike = both[0]
    return strike + math.exp(rate * years) * (calls[strike] - puts[strike])


@dataclass(frozen=True)
class PricedLeg:
    kind: str
    strike: float
    expiry: date
    mid: float
    forward: float
    sigma: float

    def value(self, day: date, rate: float, move_pct=0.0, sigma_factor=1.0, sigma_add=0.0, days=0) -> float:
        """Per unit under a shock: the forward moved, the volatility scaled and raised, `days` passed."""
        years = max((self.expiry - day).days - days, 0) / DAYS_PER_YEAR
        forward = self.forward * (1 + move_pct / 100)
        return black76(self.kind, forward, self.strike, years, rate, self.sigma * sigma_factor + sigma_add)


def years_to(expiry: date, day: date) -> float:
    return max((expiry - day).days, 0) / DAYS_PER_YEAR
