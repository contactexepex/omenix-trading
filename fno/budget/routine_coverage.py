"""Whether the data routines' sessions are captured (judge 104 addenda 1 and 2). On the measured basis their minutes sit
in the denominator, so a missed run makes the books' share look higher than it is: the measured level is not known
until every expected run is recorded. Each routine in `budget.data_routines` names its real schedule. The only one in
use is `daily`: the 3 pm quote recorder is started every calendar day at about 14:50 IST, and on a closed day it still
runs and prints "not a trading day" (CLAUDE.md), so it uses plan minutes every day. Another schedule is refused, never
guessed, until a rule is added for it. A run is recorded by the routine's own timing record (`record-usage --self-timed
--purpose data_routines --role <name>`); adding that record to a routine's prompt is the owner's step."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .constants import PURPOSE_DATA_ROUTINES

DAILY = "daily"
SCHEDULES = (DAILY,)
MISSING = "data routines not fully captured: {n} of {expected} expected run(s) recorded ({names})"
BAD_ROUTINE = "budget.data_routines entry {entry!r} needs a name and a schedule from {schedules}"


@dataclass(frozen=True)
class DataRoutine:
    name: str
    schedule: str

    @classmethod
    def from_config(cls, entries: list | None) -> list[DataRoutine]:
        routines = []
        for entry in entries or []:
            if not isinstance(entry, dict) or not entry.get("name") or entry.get("schedule") not in SCHEDULES:
                raise ValueError(BAD_ROUTINE.format(entry=entry, schedules=SCHEDULES))
            routines.append(cls(str(entry["name"]), str(entry["schedule"])))
        return routines

    def runs(self, first: date, last: date) -> list[date]:
        """Days from first to last (both included) on which this routine is started."""
        return [first + timedelta(days=n) for n in range((last - first).days + 1)]  # DAILY, the only schedule


def routine_gap(routines: list[DataRoutine], usage: list[dict], month: str, before: date) -> str:
    """Why the month's data-routine runs before `before` are not all captured, or empty when they are (or none)."""
    if not routines:
        return ""
    first = date.fromisoformat(month + "-01")
    next_month = date(first.year + first.month // 12, first.month % 12 + 1, 1)
    last = min(before, next_month) - timedelta(days=1)
    seen = {(r["role_or_bundle"], r["date"]) for r in usage if r["purpose"] == PURPOSE_DATA_ROUTINES}
    expected = [(r.name, day.isoformat()) for r in routines for day in r.runs(first, last)]
    found = sum(1 for run in expected if run in seen)
    names = ", ".join(f"{r.name} ({r.schedule})" for r in routines)
    return "" if found == len(expected) else MISSING.format(n=found, expected=len(expected), names=names)
