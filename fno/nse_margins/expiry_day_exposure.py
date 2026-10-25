"""NSE's exposure margin on an index option's own expiry day (story MS-P1m round 2; judge 491: refusing that day froze
whole control accounts). SEBI/HO/MRD/TPD-1/P/CIR/2024/132 (1 Oct 2024), para 5.6: an extra Extreme Loss Margin of 2%
"for all open short options at the start of the day, as well on short options contracts initiated during the day that
are due for expiry on that day", from 20 Nov 2024; NSE Clearing's NCL/CMPT/64639 (21 Oct 2024) levies it "on short
index options contracts" (P0 probe 4, checked). So a short index option expiring that day carries its usual 2% (3%
more than 10% out of the money) plus 2%. Every other day is A14's rule unchanged; an expiry day before 20 Nov 2024, or
a day after expiry, stays refused (not modelled)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from ..research_engine.structures import Leg
from .calculator import NseIndexOptionExposure

EXPIRY_DAY_EXTRA_RATE = 0.02  # SEBI 2024/132 para 5.6
EXPIRY_DAY_EXTRA_FROM = date(2024, 11, 20)  # its effective date


class ExpiryDayIndexExposure(NseIndexOptionExposure):
    """A14's index-option exposure, plus SEBI's extra 2% on the short options expiring that very day."""

    def per_unit(self, legs: Sequence[Leg], underlying: float, expiry: date, day: date) -> float:
        if not applies(expiry, day):
            return super().per_unit(legs, underlying, expiry, day)
        return sum((self._rate(leg, underlying) + EXPIRY_DAY_EXTRA_RATE) * underlying for leg in legs if not leg.bought)


def applies(expiry: date, day: date) -> bool:
    """Whether a figure on `day` carries the expiry-day extra (for the record)."""
    return expiry == day and day >= EXPIRY_DAY_EXTRA_FROM
