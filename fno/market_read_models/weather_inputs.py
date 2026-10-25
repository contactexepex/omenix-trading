"""What the weather page publishes (story P2a, screen W3a), read from M1's own committed records, never examples: the
session's weather record, the records of the sessions before it (the drivers' typical change, the recent strip, the
red share and the live scores) and NIFTY's committed closes (whether a 2% move came, once resolved by the day). M1's
records are read through `WeatherRecords` only; nothing here writes a record or recomputes a colour or a
probability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..forecast_v4_rules.series import DayValue, big_move_outcomes
from ..weather.records import WeatherRecords

HISTORY_SESSIONS = 251  # 250 changes for the drivers' typical change; 250 records for the red share


@dataclass(frozen=True)
class WeatherInputs:
    day: date
    record: dict | None  # the session's weather record; None when M1 wrote none
    sessions: list[date]  # the regular sessions before the day, oldest first (up to 251)
    earlier: dict[date, dict]  # those sessions' records (a session without one is absent)
    big_move: dict[date, bool]  # a session -> a 2% move came the next session (resolved by the day only)
    history: list[dict] = field(default_factory=list)  # every record up to the day, oldest first (weather_history)


class WeatherInputsReader:
    def __init__(self, records: WeatherRecords, closes: list[DayValue]):
        self.records, self.closes = records, closes

    def on(self, day: date) -> WeatherInputs:
        sessions = [c.day for c in self.closes if c.day < day][-HISTORY_SESSIONS:]
        earlier = {d: r for d in sessions if (r := self.records.for_day(d)) is not None}
        big_move = {o.day: o.value for o in big_move_outcomes(self.closes, 1) if o.resolved_on <= day}
        history = [r for c in self.closes if c.day <= day and (r := self.records.for_day(c.day)) is not None]
        return WeatherInputs(day, self.records.for_day(day), sessions, earlier, big_move, history)
