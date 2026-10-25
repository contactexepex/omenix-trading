"""Checks of the cue tables (story A17). Each lists what it finds and changes nothing: a gap is never filled, a doubtful
value never dropped.

- gaps: weekdays between a cue's first and last date without a value. Unverified: the repository has no US or UK
  holiday calendar, so a holiday and a missing value cannot be told apart;
- repeated: a value equal to the previous date's value (a publisher's holiday row or a stale value, to look at);
- usdinr overlap: RBI's and FBIL's reference rates on every date both have, with any difference listed (the summary
  gives how many dates were compared).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta

GAP_FIELDS = ("cue", "date", "kind")
OVERLAP_FIELDS = ("date", "kind")  # never a rate: with RBI's public rate, any FBIL figure would reveal FBIL's (A17d)
WEEKDAY_WITHOUT_VALUE, REPEATED = "weekday_without_value", "repeated_previous_value"
SATURDAY = 5


def gap_rows(cue: str, rows: list[dict[str, str]]) -> list[tuple[str, str, str]]:
    days = {date.fromisoformat(r["value_date"]) for r in rows}
    found = []
    if days:
        day = min(days)
        while day <= max(days):
            if day.weekday() < SATURDAY and day not in days:
                found.append((cue, day.isoformat(), WEEKDAY_WITHOUT_VALUE))
            day += timedelta(days=1)
    for before, row in zip(rows, rows[1:], strict=False):
        if float(row["value"]) == float(before["value"]):
            found.append((cue, row["value_date"], REPEATED))
    return sorted(found, key=lambda r: (r[1], r[2]))


def overlap_rows(rbi: Mapping[str, str], fbil: Mapping[str, str]) -> list[tuple[str, str]]:
    """Every date both publish where their rates differ. A date only one has is not listed here: RBI's own gaps (its
    2018-2022 hole included) are in `gaps.csv`, and FBIL's public site trails by a week."""
    shared = sorted(set(rbi) & set(fbil))
    return [(day, "differs") for day in shared if float(rbi[day]) != float(fbil[day])]
