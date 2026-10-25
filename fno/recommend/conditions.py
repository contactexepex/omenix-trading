"""The day's conditions (story REC1b, section 1): problem steps, the quote gate and the market weather, read from the
day's run log and M1's weather record. The school step is left out of the problem steps: its state is its candidate
source's (section 5), so a school that did not run never hides `no_established_version`. A weather record that is
missing, not live or not scored is an unreadable input, so the day is data_check_failed (owner, 15 Oct 2026, "4 A":
a missing or unscored reading blocks new trades)."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from ..constants import SCHOOL_STEP, STEP_OK
from ..desk.run_log import problem_steps
from ..forecast_v4_rules.records import LIVE
from ..weather.records import WeatherRecords
from .ports import ConditionsPort, DayConditions, InputFailed, open_run_log
from .refs import RecordRef

QUOTES_DONE = "quotes_done"
SCORED, RED = "scored", "RED"
COLOURS = frozenset({"GREEN", "AMBER", RED})
NO_LOG = "the run log of {day} is missing"
NO_QUOTES = "the quotes_done step is not in the run log"
NO_WEATHER = "the weather record of {day} is missing"
BAD_WEATHER = "the weather record of {day} is not a live scored colour ({label}, {status}, {colour})"


class RunLogConditions(ConditionsPort):
    def __init__(self, root: Path, weather: WeatherRecords):
        self.root, self.weather = root, weather

    def conditions(self, day: date) -> DayConditions:
        log = open_run_log(self.root, day)
        if not log.path.is_file():
            raise InputFailed(NO_LOG.format(day=day))
        if not log.done(QUOTES_DONE):
            raise InputFailed(NO_QUOTES)
        problems = [name for name, _ in problem_steps(log.steps) if name != SCHOOL_STEP]
        weather_path = self.weather.path(day)
        red = _weather_red(day, _weather_of(self.weather, day))
        used = (_ref(self.root, log.path), _ref(self.root, weather_path))
        return DayConditions(bool(problems), log.result(QUOTES_DONE).get("status") != STEP_OK, red, used)


def _weather_red(day: date, record: dict | None) -> bool:
    if record is None:
        raise InputFailed(NO_WEATHER.format(day=day))
    label, status, colour = record.get("label"), record.get("status"), record.get("colour")
    if label != LIVE or status != SCORED or colour not in COLOURS:
        raise InputFailed(BAD_WEATHER.format(day=day, label=label, status=status, colour=colour))
    return colour == RED


def _ref(root: Path, path: Path) -> RecordRef:
    try:
        data = path.read_bytes()
        json.loads(data)
    except (OSError, ValueError) as bad:  # an unreadable file is an input failure, never a pass
        raise InputFailed(f"{path.name} does not read ({type(bad).__name__})") from None
    return RecordRef(path.relative_to(root).as_posix(), hashlib.sha256(data).hexdigest())


def _weather_of(weather: WeatherRecords, day: date) -> dict | None:
    try:
        return weather.for_day(day)
    except (OSError, ValueError) as bad:
        raise InputFailed(f"the weather record of {day} does not read ({type(bad).__name__})") from None
