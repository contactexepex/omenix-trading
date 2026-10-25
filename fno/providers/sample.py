"""Deterministic synthetic data for tests and offline demos. Not real market data."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from ..analytics import bs_price
from ..models import IST, OptionChain, OptionQuote
from .base import Provider

SPOTS = {"NIFTY": 22500.0, "BANKNIFTY": 55000.0, "FINNIFTY": 25000.0}
STEPS = {"NIFTY": 50.0, "BANKNIFTY": 100.0, "FINNIFTY": 50.0}


class SampleProvider(Provider):
    name = "sample"

    def __init__(self, config: dict, as_of: datetime | None = None, spot_shift_pct: float = 0.0):
        super().__init__(config)
        self.as_of = as_of or datetime(2026, 10, 9, 15, 30, tzinfo=IST)
        self.spot_shift_pct = spot_shift_pct

    def _spot(self, underlying: str) -> float:
        return SPOTS.get(underlying.upper(), 1000.0) * (1 + self.spot_shift_pct / 100)

    def expiries(self, underlying: str) -> list[date]:
        d = self.as_of.date()
        days_to_tue = (1 - d.weekday()) % 7 or 7
        first = d + timedelta(days=days_to_tue)
        return [first + timedelta(weeks=i) for i in range(5)]

    def chain(self, underlying: str, expiry: date) -> OptionChain:
        spot = self._spot(underlying)
        step = STEPS.get(underlying.upper(), spot * 0.01)
        chain = OptionChain(
            underlying=underlying.upper(),
            spot=spot,
            expiry=expiry,
            timestamp=self.as_of,
            lot_size=self.fallback_lot_size(underlying),
            source="sample",
        )
        t = chain.years_to_expiry()
        base_strike = SPOTS.get(underlying.upper(), 1000.0)
        atm = round(base_strike / step) * step
        for i in range(-20, 21):
            k = atm + i * step
            moneyness = math.log(k / spot)
            sigma = 0.13 - 0.25 * moneyness + 1.5 * moneyness**2  # mild put skew
            for kind in ("CE", "PE"):
                price = max(bs_price(spot, k, t, 0.065, sigma, kind), 0.05)
                tick = max(0.05, round(price * 0.005, 2))
                otm = (k > spot) if kind == "CE" else (k < spot)
                oi = 50000 * math.exp(-abs(i) / 8) * (1.4 if otm else 0.6)
                chain.quotes[(k, kind)] = OptionQuote(
                    strike=k,
                    kind=kind,
                    ltp=round(price, 2),
                    bid=round(max(price - tick, 0.05), 2),
                    ask=round(price + tick, 2),
                    oi=round(oi),
                    volume=round(oi * 3),
                    iv=round(sigma * 100, 2),
                )
        return chain
