"""The smile fit and each contract's smile value (G13 section 2): a quadratic in log-moneyness `ln(K/F)` fitted by least
squares to the out-of-the-money IVs, and Black-76 at that smile for every used quote. A smoothness residual, not a
valuation and no trade signal (`SMILE_VALUE_NOTE`, judge 304 minor 1)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .chain import UsedQuotes
from .constants import MIN_SMILE_POINTS
from .pricing import black76_price, delta, implied_vol
from .surface import SmilePoint

TOO_FEW_SMILE_POINTS = "too few out-of-the-money IVs for a smile: {n} (at least {minimum})"


@dataclass(frozen=True)
class Smile:
    forward: float
    coefficients: tuple[float, float, float]  # IV (fraction) = a k^2 + b k + c, k = ln(K/F)
    rmse_points: float

    def iv(self, strike: float) -> float:
        a, b, c = self.coefficients
        k = math.log(strike / self.forward)
        return a * k * k + b * k + c


@dataclass(frozen=True)
class ContractValue:
    contract_id: str
    strike: float
    kind: str
    bid: float | None
    ask: float | None
    price: float
    iv: float | None
    delta: float | None
    smile_iv: float | None
    smile_value: float | None
    inside_spread: bool | None  # None without a two-sided quote (end of day)

    @property
    def gap_rs(self) -> float | None:
        return None if self.smile_value is None else self.smile_value - self.price

    @property
    def gap_iv_points(self) -> float | None:
        return None if self.iv is None or self.smile_iv is None else (self.iv - self.smile_iv) * 100


def fit_smile(points: tuple[SmilePoint, ...], forward: float) -> tuple[Smile | None, str | None]:
    if len(points) < MIN_SMILE_POINTS:
        return None, TOO_FEW_SMILE_POINTS.format(n=len(points), minimum=MIN_SMILE_POINTS)
    k = np.array([math.log(p.strike / forward) for p in points])
    iv = np.array([p.iv for p in points])
    a, b, c = (float(x) for x in np.polyfit(k, iv, 2))
    fitted = a * k * k + b * k + c
    rmse = float(np.sqrt(np.mean((iv - fitted) ** 2))) * 100
    return Smile(forward, (a, b, c), rmse), None


def contract_values(used: UsedQuotes, smile: Smile | None, forward: float, days: int,
                    rate: float) -> tuple[ContractValue, ...]:  # fmt: skip
    values = []
    for q in sorted(used.quotes, key=lambda q: (q.strike, q.kind)):
        iv = implied_vol(q.price, forward, q.strike, q.kind, days, rate)
        smile_iv = smile.iv(q.strike) if smile is not None else None
        usable = smile_iv is not None and smile_iv > 0
        value = black76_price(forward, q.strike, q.kind, days, rate, smile_iv) if usable else None
        inside = None if value is None or q.bid is None or q.ask is None else q.bid <= value <= q.ask
        own_delta = delta(forward, q.strike, q.kind, days, rate, iv) if iv is not None else None
        values.append(ContractValue(q.contract_id, q.strike, q.kind, q.bid, q.ask, q.price, iv, own_delta,
                                    smile_iv if usable else None, value, inside))  # fmt: skip
    return tuple(values)
