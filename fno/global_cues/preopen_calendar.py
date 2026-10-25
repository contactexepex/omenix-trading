"""Part B's question to a market's closures calendar before it reads an index (story A17f): is today a listed closure,
and does the calendar cover today (and, from 1 Dec, next year)? A calendar that cannot be loaded, or a year it does not
cover, is a problem of that index alone: the index is still read from Yahoo as if no day were listed."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from .market_closures import HOLIDAY, Closure, MarketClosures
from .preopen_outcome import INCOMPLETE, Problem

DECEMBER = 12  # from 1 Dec a missing next year is warned: the exchange publishes it late in the year
KIND_LABELS = {HOLIDAY: "holiday"}  # anything else is an unscheduled closure
REFUSED = "{index}: calendar refused ({error})"
NOT_COVERED = "{index}: {label} calendar has no {year}"
NEXT_YEAR_MISSING = NOT_COVERED + " yet"


@dataclass(frozen=True)
class CalendarVerdict:
    closure: Closure | None
    lines: tuple[str, ...] = ()
    problems: tuple[Problem, ...] = ()

    def closed_line(self, index: str, label: str) -> str:
        kind = KIND_LABELS.get(self.closure.kind, "unscheduled closure")
        return f"{index}: market closed ({label} {kind}: {self.closure.description})"


class ClosureCalendar:
    def __init__(self, label: str, load: Callable[[], MarketClosures]):
        """`label`: the exchange named in lines ("TWSE"); `load`: reads the file (ValueError or OSError when it
        cannot)."""
        self.label, self._load = label, load

    def verdict(self, index: str, day: date) -> CalendarVerdict:
        try:
            closures = self._load()
        except (ValueError, OSError) as exc:
            text = REFUSED.format(index=index, error=type(exc).__name__)
            return CalendarVerdict(None, (f"{text}: {exc}",), (Problem(text),))
        if not closures.covers(day.year):
            text = NOT_COVERED.format(index=index, label=self.label, year=day.year)
            return CalendarVerdict(None, (text,), (Problem(text),))
        if day.month == DECEMBER and not closures.covers(day.year + 1):
            text = NEXT_YEAR_MISSING.format(index=index, label=self.label, year=day.year + 1)
            return CalendarVerdict(closures.closure(day), (text,), (Problem(text, INCOMPLETE),))
        return CalendarVerdict(closures.closure(day))
