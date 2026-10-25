"""Reads an XBRL instance (the filings' machine-readable form, story A12) into plain facts: each value with the period
it covers. Only facts without dimensions (the company's own totals, not one segment's) are kept.

A context's period is the one its own DateOfStartOfReportingPeriod and DateOfEndOfReportingPeriod facts declare,
when it has them: NSE's files before the March 2025 quarter give the year-to-date context the quarter's dates in its
XBRL period (measured on TCS, September 2024: both contexts say July to September, while the facts in the second
declare April to September and hold the half-year cash flow).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

XBRLI = "{http://www.xbrl.org/2003/instance}"
DIMENSION_TAGS = (f"{XBRLI}segment", f"{XBRLI}scenario")
DECLARED_START, DECLARED_END = "DateOfStartOfReportingPeriod", "DateOfEndOfReportingPeriod"


class NotXbrl(ValueError):
    """The bytes are not an XBRL instance (an error page, a cut-off download)."""


class TruncatedXbrl(NotXbrl):
    """The bytes begin as an XBRL instance (its namespace near the start) but are not well-formed XML: a cut-off file.
    An error page never carries the XBRL namespace, so a refusal is never mistaken for one."""


XBRL_HEAD_BYTES = 4096  # the root element and its namespace declarations sit in a file's first bytes


@dataclass(frozen=True)
class Period:
    start: date | None  # None for a balance on one day (an instant)
    end: date

    @property
    def days(self) -> int:
        return 0 if self.start is None else (self.end - self.start).days + 1


@dataclass(frozen=True)
class Fact:
    name: str  # the element's local name, e.g. RevenueFromOperations
    period: Period
    text: str


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_facts(data: bytes) -> list[Fact]:
    """Every fact without dimensions; NotXbrl when the bytes are not an XBRL instance."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        cut_off = XBRLI.strip("{}").encode("ascii") in data[:XBRL_HEAD_BYTES]
        raise (TruncatedXbrl if cut_off else NotXbrl)(f"not XML: {exc}") from exc
    if root.tag != f"{XBRLI}xbrl":
        raise NotXbrl(f"root element is {local_name(root.tag)!r}, not xbrl")
    periods = _plain_periods(root)
    raw = [
        (local_name(e.tag), e.get("contextRef"), (e.text or "").strip()) for e in root if e.get("contextRef") in periods
    ]
    periods.update(_declared_periods(raw, periods))
    return [Fact(name, periods[context], text) for name, context, text in raw]


def _declared_periods(raw: list[tuple[str, str, str]], periods: dict[str, Period]) -> dict[str, Period]:
    """Context ID -> the period its own start and end facts declare (only contexts that declare both)."""
    declared: dict[str, dict[str, str]] = {}
    for name, context, text in raw:
        if name in (DECLARED_START, DECLARED_END) and text:
            declared.setdefault(context, {})[name] = text[:10]
    return {
        context: Period(date.fromisoformat(d[DECLARED_START]), date.fromisoformat(d[DECLARED_END]))
        for context, d in declared.items()
        if len(d) == 2 and periods[context].start is not None
    }


def _plain_periods(root: ET.Element) -> dict[str, Period]:
    """Context ID -> period, for contexts without a segment or scenario (dimension)."""
    periods = {}
    for context in root.iter(f"{XBRLI}context"):
        if _has_dimension(context):
            continue
        period = context.find(f"{XBRLI}period")
        if period is None:
            continue
        periods[context.get("id")] = _period(period)
    return periods


def _has_dimension(context: ET.Element) -> bool:
    return any(True for tag in DIMENSION_TAGS for _ in context.iter(tag))


def _period(period: ET.Element) -> Period:
    def day(name: str) -> date | None:
        found = period.find(f"{XBRLI}{name}")
        return None if found is None else date.fromisoformat(found.text.strip()[:10])

    instant = day("instant")
    return Period(None, instant) if instant else Period(day("startDate"), day("endDate"))
