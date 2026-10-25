"""The weather page (story P2a, screen W3a; contract `FnoWeather`, page `weather`), from M1's committed records.

- **Published** only from a live record that M1 scored. A back-fill record, a live record with a figure missing, or no
  record at all gives `not_published`, the missing input named, no colour, and new entries blocked (fail closed).
- **No levels** (owner, 16 Oct 2026): the page carries the colour, the probabilities beside their base rates and the
  drivers' values in plain words; never a driver's `reaches` colour, a threshold, or the US cue (`weather_parts.py`).
- **Labelled back-fill (contract 2.8.0):** the recent strip and the red share show the back-fill, each row and the
  share labelled; the scores are G8's (none yet). Today's colour is only ever a live record's."""

from __future__ import annotations

from ..forecast_v4_rules.records import LIVE
from ..weather.constants import WEATHER_OPERATIVE_MODEL, WeatherColour
from .blocks import BlockBuilder, SessionRows
from .weather_inputs import WeatherInputs
from .weather_parts import BASE_RATE, OK, QUESTIONS, basis, drivers, figure, is_live, recent, red_share, scores

PUBLISHED, NOT_PUBLISHED = "published", "not_published"
NO_RECORD = "M1 wrote no weather record for {day}"
NO_LIVE_RECORD = "only a back-fill (exploratory) record exists for this session: M1's live job is not running yet"
NOT_SCORED = "M1 recorded it as {status} for this session"
FIGURES = {  # a record's probability key -> (the figure in plain words, the story that provides it)
    WEATHER_OPERATIVE_MODEL: ("the weather model's chance of a 2% move", "M1"),
    BASE_RATE: ("the usual chance of a 2% move over 750 sessions", "G7"),
}


class FnoWeatherBlock(BlockBuilder):
    page_key, served_schema = "weather", "FnoWeatherResponse"

    def build(self, rows: SessionRows) -> dict:
        return weather_payload(rows.weather)


def weather_payload(inputs: WeatherInputs) -> dict:
    record, missing = inputs.record, missing_inputs(inputs)
    published = not missing
    (_, q1), (_, q5) = QUESTIONS
    p1, p5 = (figure(record, WEATHER_OPERATIVE_MODEL, q) if published else None for q in (q1, q5))
    b1, b5 = (figure(record, BASE_RATE, q) if record else None for q in (q1, q5))
    colour = record["colour"] if published else None
    return {
        "session": inputs.day.isoformat(), "status": PUBLISHED if published else NOT_PUBLISHED,
        "missing_inputs": missing, "model_version": record["operative"] if record else WEATHER_OPERATIVE_MODEL,
        "colour": colour, "blocks_new_entries": colour not in (WeatherColour.GREEN, WeatherColour.AMBER),
        "p_big_1d": p1, "p_big_5d": p5, "base_rate_1d": b1, "base_rate_5d": b5,
        "times_usual_1d": _ratio(p1, b1), "times_usual_5d": _ratio(p5, b5),
        "drivers": drivers(inputs) if published else [], "intraday": [], "recent": recent(inputs),
        "red_share": red_share(inputs), "scores": scores(basis(inputs) != LIVE),
        "price_of_calm": {"month": inputs.day.strftime("%Y-%m"), "status": "not_measured_yet", "blocked_trades": None,
                          "risk_avoided": None, "shadow_net": None},
    }  # fmt: skip


def missing_inputs(inputs: WeatherInputs) -> list[dict]:
    """Why the session has no published weather; empty when it has one."""
    record = inputs.record
    if record is None:
        return [_missing("the session's weather record", "M1", NO_RECORD.format(day=inputs.day.isoformat()))]
    if not is_live(record):
        return [_missing("the session's live weather record", "M1", NO_LIVE_RECORD)]
    return [
        _missing(f"{FIGURES[key][0]} ({label})", FIGURES[key][1], NOT_SCORED.format(status=entry["status"]))
        for key in FIGURES for label, question in QUESTIONS
        if (entry := record["probabilities"][key][question])["status"] != OK
    ]  # fmt: skip


def _missing(what: str, story: str, detail: str) -> dict:
    return {"input": what, "story": story, "detail": detail}


def _ratio(p: float | None, base: float | None) -> float | None:
    return round(p / base, 4) if p is not None and base else None
