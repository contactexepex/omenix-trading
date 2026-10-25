"""Each unit's allocated cost per opportunity: a declared split (story F9a; judge 172 blocking 1). A unit runs as a
sub-agent inside its book's one session and F8 records one usage row per session and day, so no unit has minutes of
its own. The book's cost for a day is F8's month allocation of its `books_and_roles` shares times that day's minutes of
those shares over their month's minutes, rounded down to the paisa; it is split equally across the units consulted
that day, the paise left going to the first unit in identifier order (F8's rule). The decider takes no part, so a
unit's figure is an upper bound: a conservative cost allocation, not the measured saving of removing the role. Each
scored opportunity is charged its own day's part (review 124: the cost covers the same dates as the tested net); the
mean over every consulted day is shown apart as the operating cost. A day without usage, or a month without a plan
cost, is unknown, never zero."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal

from ..budget.allocation import Allocation
from ..budget.constants import PURPOSE_BOOKS_AND_ROLES

COST_LABEL = "conservative cost allocation (declared split, upper bound; allocated, not a bill)"

MonthAllocation = Callable[[str], Allocation]  # F8's allocation of a month (YYYY-MM)


@dataclass(frozen=True)
class ConsultedDay:
    day: date
    units: tuple[str, ...]


def _book_rows(rows: Iterable[Mapping], book: str) -> list[Mapping]:
    return [r for r in rows if r["purpose"] == PURPOSE_BOOKS_AND_ROLES and r["book"] == book]


def book_day_paise(allocation: Allocation, usage: Sequence[Mapping], book: str, day: date) -> int | None:
    """The book's allocated cost for one day, in paise; None when unknown."""
    shares = [rs for (purpose, b, _), rs in allocation.allocated_rs.items() if purpose == PURPOSE_BOOKS_AND_ROLES
              and b == book]  # fmt: skip
    if not shares or any(rs is None for rs in shares):
        return None
    rows = _book_rows(usage, book)
    month = sum((Decimal(r["minutes"]) for r in rows), Decimal(0))
    today = sum((Decimal(r["minutes"]) for r in rows if r["date"] == day.isoformat()), Decimal(0))
    if month <= 0 or today <= 0:
        return None
    paise = Decimal(round(sum(shares) * 100))
    return int((paise * today / month).to_integral_value(rounding=ROUND_FLOOR))


def split_paise(paise: int, units: Sequence[str]) -> dict[str, int]:
    """Equal parts to the paisa; the remainder to the first unit in identifier order."""
    ordered = sorted(units)
    parts = dict.fromkeys(ordered, paise // len(ordered))
    parts[ordered[0]] += paise - sum(parts.values())
    return parts


def daily_parts(unit: str, days: Sequence[ConsultedDay], book: str, allocation_of: MonthAllocation,
                usage_of: Callable[[str], Sequence[Mapping]]) -> dict[date, float | None]:  # fmt: skip
    """The unit's part of the book's cost on each day its card was consulted, in rupees; None on an unknown day."""
    parts: dict[date, float | None] = {}
    for consulted in (d for d in days if unit in d.units):
        month = consulted.day.strftime("%Y-%m")
        paise = book_day_paise(allocation_of(month), usage_of(month), book, consulted.day)
        parts[consulted.day] = None if paise is None else split_paise(paise, consulted.units)[unit] / 100
    return parts


def mean_cost(costs: Iterable[float | None]) -> float | None:
    """The mean of the given daily parts, in rupees to the paisa; None when any is unknown or there is none."""
    found = list(costs)
    if not found or any(c is None for c in found):
        return None
    return round(sum(found) / len(found), 2)
