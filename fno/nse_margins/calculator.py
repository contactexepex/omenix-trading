"""Margin parts of one lot of a one-expiry option structure (story A14): SPAN scanning risk, net option value and
exposure margin, kept apart (judge 75: C2 combines them).

SPAN: the structure's loss in each of the file's 16 scenarios is the sum over its legs of the leg's side (bought +1,
sold -1) times the option's risk array; the scanning risk is the largest loss, never below zero. For one expiry there is
no calendar-spread charge, so the SPAN margin is the scanning risk, or SPAN's short-option minimum (rate times short
units, GROSS) when that is larger: zero in every file A14 reads, non-zero in 2020's (story A14c). The net option value
is the legs' value at the file's prices (bought legs plus).

Exposure: NSE's extreme-loss margin on index options, charged on each short option's notional value (the index's last
close times the quantity); long options carry none. NSE's rule changes by circular, so it sits behind `ExposureRule`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from calendar import monthrange
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from ..constants import (
    DEEP_OTM_DISTANCE,
    DEEP_OTM_EXPOSURE_RATE,
    EXPOSURE_MODEL_MAX_MONTHS,
    INDEX_OPTION_EXPOSURE_RATE,
    OPTION_CALL,
)
from ..research_engine.structures import Leg
from .span_file import SCENARIOS, SpanFile


class MarginOutsideModel(ValueError):
    """The structure or day is outside what the calculator models exactly: no margin, so no row."""


@dataclass(frozen=True)
class MarginFigure:
    span: float  # SPAN scanning risk, rupees per lot
    nov: float  # net option value at the file's prices, bought legs plus (a credit structure's is negative)
    exposure: float


class ExposureRule(ABC):
    @abstractmethod
    def per_unit(self, legs: Sequence[Leg], underlying: float, expiry: date, day: date) -> float:
        """Exposure margin of one unit of the structure, rupees; MarginOutsideModel where the rule is not modelled."""


def months_later(day: date, months: int) -> date:
    """The same day `months` later, or the month's last day when it has fewer days."""
    years, month_index = divmod(day.month - 1 + months, 12)
    year, month = day.year + years, month_index + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


class NseIndexOptionExposure(ExposureRule):
    """2% of notional per short index option, 3% when it is more than 10% out of the money. Expiry day (+2%) and
    beyond 9 months (5%) are refused: the desk never enters there, and an unmodelled rate must not pass silently."""

    def per_unit(self, legs: Sequence[Leg], underlying: float, expiry: date, day: date) -> float:
        if expiry <= day or expiry > months_later(day, EXPOSURE_MODEL_MAX_MONTHS):
            raise MarginOutsideModel(f"expiry {expiry} on {day}: expiry-day and beyond-9-month rates are not modelled")
        return sum(self._rate(leg, underlying) * underlying for leg in legs if not leg.bought)

    @staticmethod
    def _rate(leg: Leg, underlying: float) -> float:
        out_of_money = leg.strike - underlying if leg.kind == OPTION_CALL else underlying - leg.strike
        return DEEP_OTM_EXPOSURE_RATE if out_of_money > DEEP_OTM_DISTANCE * underlying else INDEX_OPTION_EXPOSURE_RATE


class SpanMarginCalculator:
    def __init__(self, exposure: ExposureRule, lot_size: int):
        self.exposure, self.lot_size = exposure, lot_size

    def per_lot(self, span: SpanFile, expiry: date, legs: Sequence[Leg], day: date) -> MarginFigure:
        options = span.series.get(expiry)
        if options is None:
            raise MarginOutsideModel(f"{span.name}: no option series for {expiry}")
        if span.tiers_holding(expiry) != 1:
            raise MarginOutsideModel(f"{span.name}: {expiry} is not in exactly one scan tier")
        missing = [leg.contract for leg in legs if leg.contract not in options]
        if missing:
            raise MarginOutsideModel(f"{span.name}: {missing} not in the {expiry} series")
        losses = [sum(leg.side * options[leg.contract].risk[i] for leg in legs) for i in range(SCENARIOS)]
        minimum = span.short_option_minimum * sum(not leg.bought for leg in legs)
        nov = sum(leg.side * options[leg.contract].price for leg in legs)
        exposure = self.exposure.per_unit(legs, span.underlying, expiry, day)
        return MarginFigure(max(0.0, minimum, *losses) * self.lot_size, nov * self.lot_size, exposure * self.lot_size)
