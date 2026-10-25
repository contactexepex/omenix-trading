"""The snapshot's chain as C4 prices it (story C4, judge 83): each contract's mid from the committed capture, each
expiry's forward from put-call parity on that expiry's own quotes, and each leg's implied volatility from its mid."""

from __future__ import annotations

from datetime import date

from .validity_evidence import Evidence
from .validity_pricing import PricedLeg, PricingProblem, implied_vol, parity_forward, years_to


class PricedChain:
    def __init__(self, evidence: Evidence, day: date, rate: float):
        self.quotes, self.day, self.rate = evidence.mids(), day, rate
        self._forwards: dict[str, float] = {}

    def mid(self, contract: str) -> float:
        if contract not in self.quotes:
            raise PricingProblem(f"{contract} has no two-sided quote in the snapshot")
        return self.quotes[contract][1]

    def forward(self, expiry: str) -> float:
        if expiry not in self._forwards:
            sides = {"CE": {}, "PE": {}}
            for (leg_expiry, strike, kind), mid in self.quotes.values():
                if leg_expiry == expiry:
                    sides[kind][strike] = mid
            years = years_to(date.fromisoformat(expiry), self.day)
            self._forwards[expiry] = parity_forward(sides["CE"], sides["PE"], years, self.rate)
        return self._forwards[expiry]

    def leg(self, contract: str) -> PricedLeg:
        mid = self.mid(contract)
        (expiry, strike, kind), forward = self.quotes[contract][0], self.forward(self.quotes[contract][0][0])
        when = date.fromisoformat(expiry)
        sigma = implied_vol(mid, kind, forward, strike, years_to(when, self.day), self.rate)
        return PricedLeg(kind, strike, when, mid, forward, sigma)
