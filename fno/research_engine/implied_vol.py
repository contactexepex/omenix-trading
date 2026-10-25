"""Implied-volatility models for research features (story B1): a strategy interface so the pricing model is chosen in
the composition root, not inside a feature.

`Black76` prices an option on the same-expiry NIFTY future (the forward, which carries interest and dividends); the
rate only discounts. `SpotBlackScholes` prices on the spot index with a fixed rate (`fno.analytics.bs_price`), which
ignores dividends and the futures basis: on 12 Oct 2026 it split call and put IVs at the ATM strike by 2.0 points where
Black-76 differs by 0.04 (tests/research_engine/test_implied_vol.py). F1 uses `Black76`.

The solver is bisection between the bounds; a price outside the prices at the bounds, or a solution at a bound, has no
implied volatility (`None`), never a clipped value.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..analytics import bs_price, norm_cdf
from ..constants import OPTION_CALL
from ..research_data.panel_reader import FutureQuote

LOWEST_VOL, HIGHEST_VOL = 0.01, 2.00  # story B1: solver bounds 1% to 200%
TOLERANCE = 1e-9  # volatility, as a fraction
MAX_STEPS = 200


@dataclass(frozen=True)
class OptionPricing:
    """One option's market price with what the models need. `underlying` is the forward (same-expiry future close)
    for Black-76 and the spot close for spot Black-Scholes."""

    price: float
    underlying: float
    strike: float
    kind: str  # "CE" or "PE"
    years: float  # calendar days to expiry / 365
    rate: float


class ImpliedVolModel(ABC):
    def __init__(self, lowest: float = LOWEST_VOL, highest: float = HIGHEST_VOL):
        self.lowest, self.highest = lowest, highest

    @abstractmethod
    def underlying(self, spot: float, future: FutureQuote | None) -> float | None:
        """The price the model is written on, from the day's spot close and same-expiry future; `None` if missing."""

    @abstractmethod
    def price(self, option: OptionPricing, sigma: float) -> float:
        """The model price at volatility `sigma` (a fraction)."""

    def implied_vol(self, option: OptionPricing) -> float | None:
        """The volatility (a fraction) whose model price equals the market price; `None` if the price is outside the
        prices at the bounds or the solution sits at a bound."""
        if option.years <= 0 or option.price <= 0 or option.underlying <= 0:
            return None
        lo, hi = self.lowest, self.highest
        if not self.price(option, lo) < option.price < self.price(option, hi):
            return None
        for _ in range(MAX_STEPS):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if self.price(option, mid) > option.price else (mid, hi)
            if hi - lo < TOLERANCE:
                break
        sigma = (lo + hi) / 2
        return None if math.isclose(sigma, self.lowest) or math.isclose(sigma, self.highest) else sigma


class Black76(ImpliedVolModel):
    def underlying(self, spot: float, future: FutureQuote | None) -> float | None:
        """The same-expiry future's close, only if it traded that day (settlement is not used for features)."""
        return future.close if future is not None and future.volume > 0 and future.close > 0 else None

    def price(self, option: OptionPricing, sigma: float) -> float:
        forward, strike, years = option.underlying, option.strike, option.years
        spread = sigma * math.sqrt(years)
        d1 = (math.log(forward / strike) + 0.5 * spread * spread) / spread
        d2 = d1 - spread
        discount = math.exp(-option.rate * years)
        if option.kind == OPTION_CALL:
            return discount * (forward * norm_cdf(d1) - strike * norm_cdf(d2))
        return discount * (strike * norm_cdf(-d2) - forward * norm_cdf(-d1))


class SpotBlackScholes(ImpliedVolModel):
    def underlying(self, spot: float, future: FutureQuote | None) -> float | None:
        return spot

    def price(self, option: OptionPricing, sigma: float) -> float:
        return bs_price(option.underlying, option.strike, option.years, option.rate, sigma, option.kind)
