"""Black-76 sensitivities of one option on its expiry's forward (story MS-INS, part b). Prices and implied volatilities
come from B1's `Black76`, the project's one pricer and inverter (as G13 uses it); only the derivatives it lacks are
here. Time is in years; theta is the change in value per year of time passing (calendar time)."""

import math
from dataclasses import dataclass

from ....analytics import norm_cdf, norm_pdf
from ....constants import OPTION_CALL
from ....research_engine.implied_vol import Black76, OptionPricing

MODEL = Black76()


@dataclass(frozen=True)
class Greeks:
    delta: float  # per rupee of forward
    gamma: float  # per rupee of forward, squared
    vega: float  # per unit of volatility (1.00 = 100 points)
    theta: float  # per year of time passing


def price(forward: float, strike: float, kind: str, years: float, rate: float, sigma: float) -> float:
    return MODEL.price(OptionPricing(0.0, forward, strike, kind, years, rate), sigma)


def implied_vol(mid: float, forward: float, strike: float, kind: str, years: float, rate: float) -> float | None:
    return MODEL.implied_vol(OptionPricing(mid, forward, strike, kind, years, rate))


def greeks(forward: float, strike: float, kind: str, years: float, rate: float, sigma: float) -> Greeks:
    root = math.sqrt(years)
    d1 = (math.log(forward / strike) + 0.5 * sigma * sigma * years) / (sigma * root)
    discount = math.exp(-rate * years)
    density = norm_pdf(d1)
    sign = 1.0 if kind == OPTION_CALL else -1.0
    value = price(forward, strike, kind, years, rate, sigma)
    return Greeks(
        delta=sign * discount * norm_cdf(sign * d1),
        gamma=discount * density / (forward * sigma * root),
        vega=discount * forward * density * root,
        theta=rate * value - discount * forward * density * sigma / (2 * root),
    )
