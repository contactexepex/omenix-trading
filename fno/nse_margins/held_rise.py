"""The stress factor each held position needed, entry to exit (story A14c; owner, 16 Oct 2026, decision 07f62385):
the smallest k for which C2c's own stressed margin of the entry's parts, `max(0, k x scan - NOV) + min(0, NOV) +
k x exposure` (`MarginParts.stressed`), covers what C2 counts (`MarginParts.initial`) on every later day held. A plain
ratio of the counted margins is not used: for a debit structure the bought legs' value nearly cancels the scan at entry,
so the ratio's small denominator measured the position losing value (3.55 in April 2020) instead of the margin the
formula must cover (1.75). For a credit structure (NOV below 0) the two are the same number.

Every trading day is an entry, for every structure and width C2 trades, on A14's expiry rule (the first monthly expiry
30 or more days out); the position is held to the last trading day at least 21 days before expiry (B2's exit). Days are
fed in order and each file is read once: open positions are carried forward.

A position whose margin cannot be computed on some day (a leg no longer listed, a method outside the model) is
dropped and named, never filled; the factor it needed up to its last computable day still counts, so a hole in the
data can never lower k. A position with no margin at entry (a bought option) has no rise."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from ..research_engine.cycles import EXIT_MIN_DAYS
from ..research_engine.structures import Leg, Structure
from ..risk.inputs import RiskInputError
from ..risk.margins import MarginParts
from .calculator import MarginOutsideModel, SpanMarginCalculator
from .span_file import SpanFile

MIN_DAYS_TO_EXPIRY = 30  # A14's entry rule (the entry window's near edge)
FACTOR_PRECISION = 1e-9  # the bisection's width; the factor returned is the upper end, so it always covers


def needed_factor(entry: MarginParts, later: float) -> float:
    """The smallest k >= 1 with `entry.stressed(k) >= later`, by bisection on C2c's own formula (it rises with k)."""
    low, high = 1.0, 2.0
    if entry.stressed(low) >= later:
        return low
    while entry.stressed(high) < later:
        low, high = high, 2 * high
    while high - low > FACTOR_PRECISION:
        middle = (low + high) / 2
        low, high = (low, middle) if entry.stressed(middle) >= later else (middle, high)
    return high


@dataclass
class Holding:
    structure: str
    width: float
    entry: date
    expiry: date
    exit: date
    legs: Sequence[Leg]
    entry_parts: MarginParts
    needed: float = 1.0  # the stress factor this holding needed so far
    peak_day: date | None = None  # the day that set `needed`
    peak_margin: float = 0.0  # what C2 counted on that day

    @property
    def entry_margin(self) -> float:
        return self.entry_parts.initial()


@dataclass
class HeldRises:
    """What a pass found: completed holdings, and the ones dropped with their reason."""

    completed: list[Holding] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


class HeldRiseTracker:
    def __init__(self, structures: Sequence[Structure], widths_for: Callable[[Structure], Sequence[float]],
                 calculator: SpanMarginCalculator, is_trading_day: Callable[[date], bool]):  # fmt: skip
        self.structures, self.widths_for, self.calculator = tuple(structures), widths_for, calculator
        self.is_trading_day = is_trading_day
        self.open: list[Holding] = []
        self.found = HeldRises()

    def feed(self, day: date, span: SpanFile, open_new: bool = True) -> None:
        """One day's file: update every open holding, close those exiting today, then open today's entries."""
        for holding in list(self.open):
            self._mark(holding, day, span)
        self.open = [h for h in self.open if h.exit > day]
        if open_new:
            self._open(day, span)

    def _mark(self, holding: Holding, day: date, span: SpanFile) -> None:
        try:
            margin = self._parts(span, holding.expiry, holding.legs, day).initial()
        except (MarginOutsideModel, RiskInputError) as exc:
            self.open.remove(holding)
            self.found.dropped.append(f"{holding.structure} {holding.width:g} entered {holding.entry}: {exc}")
            self.found.completed.append(holding)  # what it needed up to now still counts: a hole never lowers k
            return
        needed = needed_factor(holding.entry_parts, margin)
        if needed > holding.needed:
            holding.needed, holding.peak_day, holding.peak_margin = needed, day, margin
        if holding.exit == day:
            self.found.completed.append(holding)

    def _open(self, day: date, span: SpanFile) -> None:
        later = [e for e in span.monthly_expiries if (e - day).days >= MIN_DAYS_TO_EXPIRY]
        if not later:
            return
        expiry = min(later)
        exit_day = self._exit(expiry)
        if exit_day <= day:
            return
        chain = frozenset(span.series.get(expiry, {}))
        for structure in self.structures:
            for width in self.widths_for(structure):
                self._open_one(structure, width, day, span, expiry, exit_day, chain)

    def _open_one(self, structure: Structure, width: float, day: date, span: SpanFile, expiry: date, exit_day: date,
                  chain: frozenset) -> None:  # fmt: skip
        legs = structure.legs(chain, span.underlying, width)
        if legs is None:
            return  # not listed at entry: A14 writes no row for it either
        try:
            parts = self._parts(span, expiry, legs, day)
            margin = parts.initial()
        except RiskInputError:
            return  # no margin at entry (a bought option): nothing to hold
        except MarginOutsideModel as exc:
            self.found.dropped.append(f"{structure.code} {width:g} not entered {day}: {exc}")
            return
        self.open.append(Holding(structure.code, width, day, expiry, exit_day, legs, parts, 1.0, day, margin))

    def _parts(self, span: SpanFile, expiry: date, legs: Sequence[Leg], day: date) -> MarginParts:
        figure = self.calculator.per_lot(span, expiry, legs, day)
        return MarginParts(figure.span, figure.nov, figure.exposure, "held position")

    def _exit(self, expiry: date) -> date:
        day = expiry - timedelta(days=EXIT_MIN_DAYS)
        while not self.is_trading_day(day):
            day -= timedelta(days=1)
        return day
