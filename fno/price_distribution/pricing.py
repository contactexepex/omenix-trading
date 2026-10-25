"""Black-76 for G13, always through B1's `implied_vol.Black76` (the project's one IV inverter, G7b's builder's
request); only the lognormal helpers the tails and deltas need are added here."""

from __future__ import annotations

import math

from ..analytics import norm_cdf
from ..constants import OPTION_CALL
from ..research_engine.implied_vol import Black76, OptionPricing
from .constants import DAYS_PER_YEAR

MODEL = Black76()


def years(days: int) -> float:
    return days / DAYS_PER_YEAR


def discount(rate: float, days: int) -> float:
    return math.exp(-rate * years(days))


def implied_vol(price: float, forward: float, strike: float, kind: str, days: int, rate: float) -> float | None:
    return MODEL.implied_vol(OptionPricing(price, forward, strike, kind, years(days), rate))


def black76_price(forward: float, strike: float, kind: str, days: int, rate: float, sigma: float) -> float:
    return MODEL.price(OptionPricing(0.0, forward, strike, kind, years(days), rate), sigma)


def d1_d2(forward: float, strike: float, sigma: float, days: int) -> tuple[float, float]:
    spread = sigma * math.sqrt(years(days))
    d1 = (math.log(forward / strike) + 0.5 * spread * spread) / spread
    return d1, d1 - spread


def delta(forward: float, strike: float, kind: str, days: int, rate: float, sigma: float) -> float:
    """Black-76 delta to the future: `e^{-rT} N(d1)` for a call, `-e^{-rT} N(-d1)` for a put."""
    d1, _ = d1_d2(forward, strike, sigma, days)
    sign = 1.0 if kind == OPTION_CALL else -1.0
    return sign * discount(rate, days) * norm_cdf(sign * d1)
