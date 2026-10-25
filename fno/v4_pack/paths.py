"""Where a day's pack and its release record live in Drive's data area (story G10 part 2, sections 1-2); GitHub holds
each one's receipt under `receipts/` (story O9)."""

from __future__ import annotations

from datetime import date

PACKS_FOLDER = "v4/packs"
PACK_PATH = PACKS_FOLDER + "/{year}/{day}.json"
DAYS_FOLDER = "v4/days"  # every release record, one per scored session, by year
RELEASE_PATH = DAYS_FOLDER + "/{year}/{day}.json"
DEADLINES_FOLDER = "v4/deadlines"  # the 15:10 verdicts, one file per scored session (G10 completion, criterion 7)
DEADLINE_PATH = DEADLINES_FOLDER + "/{year}/{day}.json"
LIVE_RECORDS_FOLDER = "v4/records/live"  # G7b's Drive-stored live records: <forecaster>/<question>/<YYYY>/<date>.json


def pack_path(day: date) -> str:
    return PACK_PATH.format(year=day.year, day=day.isoformat())


def release_path(day: date) -> str:
    return RELEASE_PATH.format(year=day.year, day=day.isoformat())


def deadline_path(day: date) -> str:
    return DEADLINE_PATH.format(year=day.year, day=day.isoformat())
