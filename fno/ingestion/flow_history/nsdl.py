"""Reads NSDL's FPI archive answer (story A23, scope 5): "Daily Trends in FPI Investments up to <date>", every
reporting date from the 1st of that month to the date. Kept: the cash section, per reporting date, category (Equity,
Debt and its limits, Hybrid, Mutual Funds, AIFs, Total) and route, gross purchases, gross sales and net (crores and
US$ million), and the day's USD/INR rate. The month's and year's totals and the derivatives section after the daily
rows are left out (sums of the days; NSE's FII statistics hold the derivatives).

NSDL spans the date and category cells over their rows and gives "Total" no span over the route column, so rows are
read by their cell count, carrying the date and category from above. Any other shape is `BadAnswer`; NSDL's note says
a reporting date's figures are the FPIs' trades of the previous trading day."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, datetime

TITLE = re.compile(r"Daily Trends in FPI Investments up to (\d{2}-[A-Za-z]{3}-\d{4})")
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
TAG = re.compile(r"<[^>]+>")
REPORTING_DATE = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$")
HEADER = ("Reporting Date", "Debt/Equity", "Investment Route", "Gross Purchases(Rs Crore)", "Gross Sales(Rs Crore)",
          "Net Investment (Rs Crore)")  # fmt: skip
DERIVATIVES = "Derivative Products"
TOTAL, PERIOD_TOTAL, RATE_PREFIX = "Total", "Total for", "Rs."
MEASURES = ("gross_purchases_crores", "gross_sales_crores", "net_crores", "net_usd_million")


class BadAnswer(ValueError):
    """Not NSDL's archive answer in the layout read here: nothing of it is used."""


@dataclass(frozen=True)
class FpiRow:
    reporting_date: date
    category: str
    route: str  # "" for the Total row
    values: tuple[float, float, float, float]  # MEASURES, in order


@dataclass(frozen=True)
class FpiMonth:
    up_to: date
    rows: list[FpiRow]
    usd_inr: dict[date, float]


def read_fpi_month(page: str, asked: date) -> FpiMonth:
    found = TITLE.search(page)
    if not found or _day(found.group(1)) != asked:
        raise BadAnswer(f"no 'Daily Trends in FPI Investments up to {asked:%d-%b-%Y}' title")
    rows, rates, current, category, header_seen = [], {}, None, "", False
    for cells in (_texts(row) for row in ROW.findall(page[found.end() :])):
        if not cells:
            continue
        if DERIVATIVES in cells or cells[0].startswith(PERIOD_TOTAL):  # "Total for January": the daily rows end
            break
        if cells[0] == HEADER[0]:
            header_seen = _check_header(cells)
            continue
        if not header_seen:
            continue
        if REPORTING_DATE.match(cells[0]):
            current, rate = _day(cells[0]), cells[-1]
            rates[current] = _rate(rate)
            cells = cells[1:-1]
        if current is None:
            raise BadAnswer("a figures row before any reporting date")
        category, row = _row(cells, current, category)
        rows.append(row)
    _check_dates(rows, asked)
    return FpiMonth(asked, rows, rates)


def _row(cells: list[str], day: date, category: str) -> tuple[str, FpiRow]:
    if len(cells) == 6:
        category, route, numbers = cells[0], cells[1], cells[2:]
    elif len(cells) == 5:
        route, numbers = cells[0], cells[1:]
        if route == TOTAL:
            category, route = TOTAL, ""
    else:
        raise BadAnswer(f"{day}: a row of {len(cells)} cells")
    return category, FpiRow(day, category, route, tuple(_number(n) for n in numbers))


def _check_header(cells: list[str]) -> bool:
    if tuple(cells[: len(HEADER)]) != HEADER:
        raise BadAnswer(f"unexpected columns {cells}")
    return True


def _check_dates(rows: list[FpiRow], asked: date) -> None:
    days = {row.reporting_date for row in rows}
    if any(day > asked or (day.year, day.month) != (asked.year, asked.month) for day in days):
        raise BadAnswer(f"a reporting date outside {asked:%b %Y} up to {asked}")
    missing = sorted(day for day in days if not any(r.reporting_date == day and r.category == TOTAL for r in rows))
    if missing:
        raise BadAnswer(f"no Total row for {missing}")


def _texts(row: str) -> list[str]:
    return [" ".join(html.unescape(TAG.sub(" ", cell)).split()) for cell in CELL.findall(row)]


def _day(text: str) -> date:
    return datetime.strptime(text, "%d-%b-%Y").date()


def _number(text: str) -> float:
    """NSDL writes a negative figure in brackets: (1001.35)."""
    negative = text.startswith("(") and text.endswith(")")
    try:
        value = float(text.strip("()").replace(",", ""))
    except ValueError as exc:
        raise BadAnswer(f"not a number: {text!r}") from exc
    return -value if negative else value


def _rate(text: str) -> float:
    if not text.startswith(RATE_PREFIX):
        raise BadAnswer(f"no USD/INR rate ({text!r})")
    return _number(text.removeprefix(RATE_PREFIX))
