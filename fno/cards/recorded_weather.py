"""The card's weather section (story T1c): the day's market weather as M1 recorded it, read from the committed record
so its SHA-256 goes into the card's footer. It never computes a colour and never shows a driver (the private US flag
stays out). Owner rule (15 Oct 2026, "4 A"): a missing or unscored reading blocks new trades, and the card says so."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date

from ..constants import V6_BIG_MOVE_1S, V6_BIG_MOVE_5S
from ..forecast_v4_rules.records import LIVE
from ..weather.constants import WeatherColour
from .committed import CommittedRecords
from .sections import WEATHER_BLOCKS as BLOCKS
from .sections import CardSection, UsedRecord, WeatherSource

SCORED, BASE_RATE, OK = "scored", "base_rate", "ok"  # M1's record values (fno/weather/day.py)
NO_READING = "Weather: no reading for {day}"
NOT_SCORED = "Weather: not scored for {day} ({why})"
COLOUR = "Weather: {colour} ({operative}, {proof})"
NOT_LIVE = "Weather: no live reading for {day} (the record is {label}, not today's weather)"
CHANCES = "Chance of a 2% NIFTY move: next session {p1} (base rate {b1}); within 5 sessions {p5} (base rate {b5})"
V0 = "Checklist v0: {colour}"
V0_NOT_SCORED = "Checklist v0: not scored ({why})"
BAD_COLOUR = "colour {!r} is not GREEN, AMBER or RED"  # a guard: M1 writes only those or "not scored"
CHANCE_MISSING = "a chance or base rate is missing"  # a guard: M1 never writes it as scored
NO_REASON = "no reason recorded"  # back-fills written before M1 added `v0_status` (16 Oct 2026)
RED_BLOCKS = "RED: no new entries (owner rule)."
MISSING_RECORD, MISSING_SCORE = "weather record for {day}", "weather not scored for {day}"
MISSING_LIVE = "live weather record for {day}"
NOT_SCORED_PREFIX = f"{WeatherColour.NOT_SCORED}: "
SHOWN = (WeatherColour.GREEN, WeatherColour.AMBER, WeatherColour.RED)  # any other colour is treated as not scored


class RecordedWeather(WeatherSource):
    """`path`: M1's own record path for a day (`WeatherRecords.path`), relative to the repository."""

    def __init__(self, records: CommittedRecords, path: Callable[[date], str]):
        self.records, self.path = records, path

    def weather(self, day: date) -> CardSection:
        path = self.path(day)
        data = self.records.read(path)
        record = _parsed(data)
        if record is None or record.get("day") != day.isoformat():
            return _blocked(NO_READING.format(day=day), MISSING_RECORD.format(day=day))
        used, chances, status = (UsedRecord.of(path, data),), _chances(record), record.get("status")
        if record.get("label") != LIVE:  # a back-fill is history, never today's reading (M1's builder, 23 Oct)
            return _blocked(NOT_LIVE.format(day=day, label=record.get("label")), MISSING_LIVE.format(day=day), used)
        colour = record.get("colour")
        if status != SCORED or colour not in SHOWN or chances is None:
            why = _why(status) if status != SCORED else CHANCE_MISSING if chances is None else BAD_COLOUR.format(colour)
            return _blocked(NOT_SCORED.format(day=day, why=why), MISSING_SCORE.format(day=day), used)
        return CardSection("weather", _scored_lines(record, chances), used)


def _parsed(data: bytes | None) -> dict | None:
    try:
        record = json.loads(data) if data is not None else None
    except ValueError:
        return None
    return record if isinstance(record, dict) else None


def _blocked(line: str, missing: str, used: tuple[UsedRecord, ...] = ()) -> CardSection:
    return CardSection("weather", (line, BLOCKS), used, (missing,))


def _why(status) -> str:
    text = str(status or "")
    return text.removeprefix(NOT_SCORED_PREFIX) or NO_REASON


def _chances(record: dict) -> dict[str, str] | None:
    """The operative forecaster's two chances and the two base rates, one decimal; None when any is missing or not a
    real chance (a malformed record fails closed, never raises)."""
    probabilities, operative = record.get("probabilities"), record.get("operative")
    wanted = {"p1": (operative, V6_BIG_MOVE_1S), "b1": (BASE_RATE, V6_BIG_MOVE_1S),
              "p5": (operative, V6_BIG_MOVE_5S), "b5": (BASE_RATE, V6_BIG_MOVE_5S)}  # fmt: skip
    found = {}
    for key, (name, question) in wanted.items():
        forecaster = probabilities.get(name) if isinstance(probabilities, dict) else None
        entry = forecaster.get(question) if isinstance(forecaster, dict) else None
        value = entry.get("value") if isinstance(entry, dict) and entry.get("status") == OK else None
        if not _is_chance(value):
            return None
        found[key] = f"{value:.1%}"
    return found


def _is_chance(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and 0 <= value <= 1  # NaN and inf fail it


def _scored_lines(record: dict, chances: dict[str, str]) -> tuple[str, ...]:
    lines = [COLOUR.format(colour=record["colour"], operative=record.get("operative"), proof=record.get("proof")),
             CHANCES.format(**chances), _v0_line(record)]  # fmt: skip
    if record["colour"] == WeatherColour.RED:
        lines.append(RED_BLOCKS)
    return tuple(lines)


def _v0_line(record: dict) -> str:
    if record.get("v0_colour") == WeatherColour.NOT_SCORED:
        return V0_NOT_SCORED.format(why=_why(record.get("v0_status")))
    return V0.format(colour=record.get("v0_colour"))
