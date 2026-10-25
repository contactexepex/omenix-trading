"""The coverage check before any stress-factor row (story A14c; ChatGPT review 117): the archive must hold the
first-archived `i1` file of every required session, checked date by date, never by a count (a same-count archive with
a different missing date, or one ending a session early, would pass a count). The required sessions are every session
of NSE's calendar (A7: regular and special, not muhurat-only) from the first session through the latest session before
the run day; the archive is A9's manifest (one row per first-archived file, with its SHA-256)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta

FIRST_SESSION = date(2020, 1, 2)  # NSE's first i1 file the recompute reads (owner, 15 Oct 2026: since 1 Jan 2020)


@dataclass(frozen=True)
class Coverage:
    through: date  # the latest required session
    files: Mapping[date, str]  # every required session -> its file's SHA-256 (complete: no gaps)


class CoverageGap(RuntimeError):
    """Required sessions without an archived file: no row may be written."""


def required_sessions(run_day: date, is_trading_day: Callable[[date], bool], first: date = FIRST_SESSION) -> list[date]:
    """Every trading session from `first` through the latest one before `run_day`."""
    days, day = [], first
    while day < run_day:
        if is_trading_day(day):
            days.append(day)
        day += timedelta(days=1)
    return days


def check_coverage(required: list[date], archived: Mapping[date, str]) -> Coverage:
    """The archive's files for every required session; a missing date is named (the first ten, then a count)."""
    if not required:
        raise CoverageGap("no required session before the run day")
    gaps = [day for day in required if day not in archived]
    if gaps:
        named = ", ".join(d.isoformat() for d in gaps[:10]) + (f" and {len(gaps) - 10} more" if len(gaps) > 10 else "")
        raise CoverageGap(f"{len(gaps)} required session(s) have no archived i1 file: {named}")
    return Coverage(required[-1], {day: archived[day] for day in required})
