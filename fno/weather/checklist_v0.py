"""Weather baseline v0: response 94's frozen rule (`research/2026-10-14-weekly-weather/PROTOCOL.md` section 5),
computed exactly as its study (`study.py`, `weather`) on a row index `i` of (day, close, VIX) rows:

- `vix_ratio` = VIX / the median VIX of the previous 250 rows;
- `vix_change5` = VIX / the VIX 5 rows earlier - 1;
- `move5` = the largest absolute simple close-to-close return of the last 5 rows;
- `rv10` = sqrt(252 x the mean squared log return of the last 10 rows), not demeaned.

RED if any of 1.30 / +20% / 2.0% / 25%; AMBER if any of 1.10 / +10% / 1.25% / 18% or a scheduled event; else GREEN.
The rule is frozen: never retuned here."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date

from .constants import WeatherColour

MEDIAN_ROWS, CHANGE_ROWS, MOVE_ROWS, RV_ROWS = 250, 5, 5, 10
RED_LIMITS = (1.30, 0.20, 0.020, 0.25)  # vix_ratio, vix_change5, move5, rv10
AMBER_LIMITS = (1.10, 0.10, 0.0125, 0.18)


@dataclass(frozen=True)
class Row:
    day: date
    close: float
    vix: float | None  # None: no India VIX close committed for the session


@dataclass(frozen=True)
class V0Inputs:
    vix_ratio: float
    vix_change5: float
    move5: float
    rv10: float

    def values(self) -> tuple[float, float, float, float]:
        return self.vix_ratio, self.vix_change5, self.move5, self.rv10


@dataclass(frozen=True)
class Event:
    day: date
    kind: str
    announced: date


def v0_inputs(rows: list[Row], i: int) -> V0Inputs | None:
    """The four inputs at row `i`, from rows up to and including `i`; None without 250 earlier rows or a VIX close."""
    if i < MEDIAN_ROWS or i >= len(rows) or any(r.vix is None for r in rows[i - MEDIAN_ROWS : i + 1]):
        return None
    vix = rows[i].vix
    ratio = vix / statistics.median(r.vix for r in rows[i - MEDIAN_ROWS : i])
    change = vix / rows[i - CHANGE_ROWS].vix - 1
    move = max(abs(rows[j].close / rows[j - 1].close - 1) for j in range(i - MOVE_ROWS + 1, i + 1))
    logs = [math.log(rows[j].close / rows[j - 1].close) for j in range(i - RV_ROWS + 1, i + 1)]
    return V0Inputs(ratio, change, move, math.sqrt(252 * sum(r * r for r in logs) / len(logs)))


def colour_as_of_close(rows: list[Row], i: int, events: list[Event], entry: date, expiry: date) -> WeatherColour:
    """The study's own mode, only to reproduce response 94: closes up to and including row `i` (every session, as
    `study.py` reads them), and its event window: announced by row `i`'s day, dated after `entry` up to `expiry`."""
    event = any(e.announced <= rows[i].day and entry < e.day <= expiry for e in events)
    return v0_colour(v0_inputs(rows, i), event)


def v0_colour(inputs: V0Inputs, event: bool) -> WeatherColour:
    values = inputs.values()
    if any(v >= limit for v, limit in zip(values, RED_LIMITS, strict=True)):
        return WeatherColour.RED
    if event or any(v >= limit for v, limit in zip(values, AMBER_LIMITS, strict=True)):
        return WeatherColour.AMBER
    return WeatherColour.GREEN


def crossed(inputs: V0Inputs) -> dict[str, str]:
    """Each input's name -> the v0 colour its value alone reaches (the drivers' line)."""
    names = ("vix_ratio", "vix_change5", "move5", "rv10")
    levels = zip(inputs.values(), RED_LIMITS, AMBER_LIMITS, strict=True)
    return {name: _level(value, red, amber) for name, (value, red, amber) in zip(names, levels, strict=True)}


def _level(value: float, red: float, amber: float) -> WeatherColour:
    if value >= red:
        return WeatherColour.RED
    return WeatherColour.AMBER if value >= amber else WeatherColour.GREEN
