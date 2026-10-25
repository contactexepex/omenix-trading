"""The market weather's fixed values (story M1, design 2.3): its forecasters, colours and the owner's thresholds.
Moved here whole from `fno/constants.py` when that file reached its 350-line limit (story E4c, orchestrator, 15 Oct
2026)."""

from __future__ import annotations

from enum import StrEnum

# The market weather (story M1, fno/weather/; design 2.3): its forecasters, colours and the owner's thresholds
# (15 Oct 2026, "Weather thresholds accepted"), scored on protocol v4's V6a and V6b
WEATHER_MODEL_VIX, WEATHER_BASELINE_V0 = "weather_vix_v1", "weather_checklist_v0"
WEATHER_OPERATIVE_MODEL = WEATHER_MODEL_VIX  # decision 71: back to v0 only by a recorded decision
WEATHER_OPERATIVE_PROVEN = False  # "not yet proven" until G8 scores it against v0 and the base rate


class WeatherColour(StrEnum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    NOT_SCORED = "not scored"  # a probability or base rate missing: blocks new trades like RED (owner "4 A")


WEATHER_RED_FLOORS, WEATHER_AMBER_FLOORS = (0.10, 0.35), (0.06, 0.20)  # (next session, within 5 sessions)
WEATHER_RED_MULTIPLE, WEATHER_AMBER_MULTIPLE = 2.5, 1.5  # times the 750-session base rate
WEATHER_RED_MAX_SHARE, WEATHER_RED_SHARE_RECORDS = 0.15, 250  # over it: "over_alarming" (never retuned in place)
WEATHER_US_CUES = ("sp500", "nasdaq100")  # private cues (owner a927390): the US-move flag is kept in Drive only
