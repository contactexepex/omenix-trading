"""The weather's colour from its two probabilities and their base rates (owner, 15 Oct 2026; design 2.3): RED when
`p1 >= max(10%, 2.5 b1)` or `p5 >= max(35%, 2.5 b5)`, AMBER at 6% / 20% and 1.5 times, else GREEN; `not scored`
when any of the four figures is missing (owner "4 A": it blocks new trades like RED)."""

from __future__ import annotations

from .constants import (
    WEATHER_AMBER_FLOORS,
    WEATHER_AMBER_MULTIPLE,
    WEATHER_RED_FLOORS,
    WEATHER_RED_MULTIPLE,
    WeatherColour,
)

# 1.5 x 0.20 is 0.30000000000000004 in floating point: without this, a share exactly at a threshold would miss it.
# Shares move in steps of 1/750 (about 1e-3), so 1e-12 never lifts a value that is truly under.
AT_THRESHOLD = 1e-12


def _reaches(probabilities, base_rates, floors, multiple) -> bool:
    pairs = zip(probabilities, base_rates, floors, strict=True)
    return any(p >= max(floor, multiple * b) - AT_THRESHOLD for p, b, floor in pairs)


def weather_colour(p1: float | None, p5: float | None, b1: float | None, b5: float | None) -> WeatherColour:
    if None in (p1, p5, b1, b5):
        return WeatherColour.NOT_SCORED
    probabilities, base_rates = (p1, p5), (b1, b5)
    if _reaches(probabilities, base_rates, WEATHER_RED_FLOORS, WEATHER_RED_MULTIPLE):
        return WeatherColour.RED
    if _reaches(probabilities, base_rates, WEATHER_AMBER_FLOORS, WEATHER_AMBER_MULTIPLE):
        return WeatherColour.AMBER
    return WeatherColour.GREEN
