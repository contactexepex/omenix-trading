"""The weather record (story M1): `research/forecasts/v4/weather/<YYYY>/<d>.json`, one per regular session, written
once (the same bytes again change nothing; a different record for a day already written is refused). Public inputs
only: the US-move flag is in the private Drive part (decision 72). The card (T1c) reads a day's committed bytes at
`WeatherRecords.path`, never the working tree; `for_day` reads the file on disk."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..forecast_v4_rules.records import LIVE, RecordConflict
from .constants import WEATHER_RED_MAX_SHARE, WEATHER_RED_SHARE_RECORDS, WeatherColour

NOT_ENOUGH = "not enough data yet"


def encode(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8")


class WeatherRecords:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def path(self, d: date) -> Path:
        return self.folder / f"{d:%Y}" / f"{d.isoformat()}.json"

    def for_day(self, d: date) -> dict | None:
        file = self.path(d)
        return _read(file) if file.is_file() else None

    def write(self, d: date, document: dict) -> bool:
        """True when written, False when the same record (`made_at` aside: a rerun) is there; else RecordConflict."""
        file, data = self.path(d), encode(document)
        if file.is_file():
            if _without_made_at(_read(file)) != _without_made_at(document):
                raise RecordConflict(f"weather {d}: a different record is already written")
            return False
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        return True

    def live_colours_before(self, d: date) -> list[str]:
        """The operative colours of the live records before `d`, oldest first."""
        found = []
        for file in sorted(self.folder.glob("*/*.json")):
            record = _read(file)
            if record["label"] == LIVE and date.fromisoformat(record["day"]) < d:
                found.append(record["colour"])
        return found

    def first_live(self) -> date | None:
        """The earliest live record's day (the back-fill stops before it)."""
        days = [date.fromisoformat(r["day"]) for r in map(_read, self.folder.glob("*/*.json")) if r["label"] == LIVE]
        return min(days, default=None)


def _read(file: Path) -> dict:
    return json.loads(file.read_text())


def _without_made_at(document: dict) -> dict:
    return {**document, "made_at": ""}


def red_share(earlier_live: list[str], today: str) -> dict:
    """RED's share of the most recent 250 live records (today's included) and whether it is over 15%."""
    recent = [*earlier_live, today][-WEATHER_RED_SHARE_RECORDS:]
    if len(recent) < WEATHER_RED_SHARE_RECORDS:
        return {"red_share": NOT_ENOUGH, "over_alarming": NOT_ENOUGH}
    share = sum(c == WeatherColour.RED for c in recent) / len(recent)
    return {"red_share": share, "over_alarming": share > WEATHER_RED_MAX_SHARE}
