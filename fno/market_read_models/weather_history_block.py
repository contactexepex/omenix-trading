"""The weather's history page (story P2a, screen W3a; `FnoWeatherHistory` 2.10.0, page `weather_history`): every
session's colour, label and two chances of a big move beside the usual chances from M1's records, oldest first, and
the counts by colour and label.

The owner kept the weather levels public (16 Oct 2026, ad562ca1), so the chances are back (2.9). Still never sent: an
input's value, its `reaches` colour, a level, or the US cue."""

from __future__ import annotations

from ..forecast_v4_rules.records import BACKFILL, LIVE
from ..weather.constants import WEATHER_OPERATIVE_MODEL, WeatherColour
from .blocks import BlockBuilder, SessionRows
from .weather_parts import BASE_RATE, QUESTIONS, colour_of, figure

COUNTED = {"green": WeatherColour.GREEN, "amber": WeatherColour.AMBER, "red": WeatherColour.RED}


class FnoWeatherHistoryBlock(BlockBuilder):
    page_key, served_schema = "weather_history", "FnoWeatherHistoryResponse"

    def build(self, rows: SessionRows) -> dict:
        return weather_history(rows.weather.history)


def chances(record: dict) -> dict:
    """The operative model's two chances of a big move beside the usual chances (null when not scored)."""
    (_, q1), (_, q5) = QUESTIONS
    model, base = WEATHER_OPERATIVE_MODEL, BASE_RATE
    return {"p_big_1d": figure(record, model, q1), "p_big_5d": figure(record, model, q5),
            "base_rate_1d": figure(record, base, q1), "base_rate_5d": figure(record, base, q5)}  # fmt: skip


def weather_history(records: list[dict]) -> dict:
    sessions = [{"session": r["day"], "colour": colour_of(r), "label": r["label"], **chances(r)} for r in records]
    colours = [s["colour"] for s in sessions]
    labels = [s["label"] for s in sessions]
    counts = {name: colours.count(colour) for name, colour in COUNTED.items()}
    counts |= {"not_scored": colours.count(None), "live": labels.count(LIVE), "backfill": labels.count(BACKFILL)}
    return {"sessions": sessions, "counts": counts}
