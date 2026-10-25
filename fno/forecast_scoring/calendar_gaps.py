"""Live days whose risk-neutral baseline is missing because the session calendar ended (owner, 16 Oct 2026, option A of
response 241; no frozen code changes). The frozen `ForecastHistory.horizon_day` asks the calendar for the next 45 days
in one call, so once that window reaches a year the calendar does not cover yet, the 20-session target day is unknown:
baseline A gives no Q1 or Q2, and Book 1's Q1 and Q2, the mean of baseline A and the base rate (book1_method.py), are
the base rate alone on those days (judge 253). Reported, never rescored.

A day is labelled only when the calendar is the only cause: baseline A's Q1 or Q2 is empty although the day's pack
shows every other input of baseline A (no input problem, an IV30), and the 45-day window crosses into the next year.
A day with an input problem is not labelled, so the count can be below the window's sessions. Known limit: a
near-future contract expiring that very day would also leave baseline A empty; inside this window the calendar is a
cause either way."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path

from ..constants import BASELINE_RISK_NEUTRAL, FORECAST_Q1_UP_20D, FORECAST_Q2_MOVE_3PCT_20D
from ..forecast.record_files import read_records_v2

LABEL = "baseline missing: calendar"
QUESTIONS = (FORECAST_Q1_UP_20D, FORECAST_Q2_MOVE_3PCT_20D)
LOOKAHEAD = timedelta(days=45)  # the frozen fno/forecast/history.py CALENDAR_LOOKAHEAD_DAYS
RECORDS, PACK = "_forecasts.csv", "_pack.json"


def calendar_limited_days(folder: Path, unverified: Iterable[str] = ()) -> list[dict]:
    """Each labelled live day, oldest first: {day, questions, label}. Days not matching their receipt are left out
    (G4 lists them apart and scores none of them)."""
    skip, found = set(unverified), []
    for records_path in sorted(folder.glob(f"*/*{RECORDS}")):
        day = date.fromisoformat(records_path.name.removesuffix(RECORDS))
        pack_path = records_path.with_name(f"{day.isoformat()}{PACK}")
        if day.isoformat() in skip or not pack_path.is_file():
            continue
        missing = _missing_baseline(records_path.read_text(encoding="utf-8"))
        if missing and _only_the_target_missing(json.loads(pack_path.read_text(encoding="utf-8")), day):
            found.append({"day": day.isoformat(), "questions": missing, "label": LABEL})
    return found


def _missing_baseline(text: str) -> list[str]:
    rows = [r.record for r in read_records_v2(text) if r.record.book == BASELINE_RISK_NEUTRAL]
    return sorted(r.question for r in rows if r.question in QUESTIONS and r.probability is None)


def _only_the_target_missing(pack: dict, day: date) -> bool:
    return not pack.get("problems") and pack.get("iv30") is not None and (day + LOOKAHEAD).year > day.year
