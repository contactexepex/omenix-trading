"""The weather page's parts from M1's records (story P2a): drivers, the recent strip, the red share and the scores.

- **Drivers** (story W3, privacy rule 4): each of v0's inputs that changed since the previous session's record, its
  value in plain words; `push` is the sign of that change (up: riskier). They are ordered by the size of the change
  against the input's own typical (median) change over the last 250 records, never by a model coefficient. The
  scheduled events of the next 5 sessions follow, each riskier; when M1 could not know them (its calendar ends inside
  the window), one driver says so. No `reaches` colour, no level, no US cue.
- **Recent, red share:** every record, each labelled live or back-fill (exploratory, contract 2.8.0); the red share
  counts live records once any exists, else the back-fill, and says which (`basis`), as M1 counts it.
- **Scores:** G8's alone (`scores()`); none yet, so not_enough_data with no number, exploratory while only the
  back-fill exists."""

from __future__ import annotations

import statistics

from ..constants import V6_BIG_MOVE_1S, V6_BIG_MOVE_5S
from ..forecast_v4_rules.records import BACKFILL, LIVE
from ..weather.constants import (
    WEATHER_RED_MAX_SHARE,
    WEATHER_RED_SHARE_RECORDS,
    WeatherColour,
)
from .weather_inputs import WeatherInputs

BASE_RATE, OK = "base_rate", "ok"
QUESTIONS = (("V6_1d", V6_BIG_MOVE_1S), ("V6_5d", V6_BIG_MOVE_5S))
YARDSTICKS = ("base_rate", "v0_checklist")  # the contract's two yardsticks
RECENT_SESSIONS = 10
EVENTS_UNKNOWN = "Scheduled events over the next 5 sessions not known yet: NSE's next-year holiday list is not loaded"
N_NEEDED = 10  # the contract: twice V6's 5-session block
DRIVERS = {  # v0's input -> (the contract's driver, its value in plain words)
    "vix_ratio": ("vix_level", lambda v: f"India VIX at {v:.2f} times its median of the previous 250 sessions"),
    "vix_change5": ("vix_change", lambda v: f"India VIX {'up' if v >= 0 else 'down'} {abs(v):.0%} over 5 sessions"),
    "move5": ("recent_big_moves", lambda v: f"NIFTY's largest daily move in the last 5 sessions: {v:.1%}"),
    "rv10": ("realised_volatility", lambda v: f"NIFTY's realised volatility over 10 sessions: {v:.0%} a year"),
}
EVENTS = {"budget": "Union Budget", "rbi_policy": "RBI policy decision", "election_result": "Election results"}


def is_live(record: dict | None) -> bool:
    return record is not None and record["label"] == LIVE


def figure(record: dict, key: str, question: str) -> float | None:
    entry = record["probabilities"][key][question]
    return entry["value"] if entry["status"] == OK else None


def colour_of(record: dict | None) -> str | None:
    """A record's colour; None without a record or for a day M1 could not score."""
    if record is None or record["colour"] == WeatherColour.NOT_SCORED:
        return None
    return record["colour"]


def basis(inputs: WeatherInputs) -> str:
    """Live once any live record exists up to the day; until then the back-fill, labelled exploratory (2.8.0)."""
    return LIVE if any(map(is_live, [*inputs.earlier.values(), inputs.record])) else BACKFILL


def drivers(inputs: WeatherInputs) -> list[dict]:
    """v0's inputs that changed since the previous session's record, strongest change first, then the events."""
    record, history = inputs.record, [inputs.earlier.get(d) for d in inputs.sessions]
    moved = []
    for name, (driver, words) in DRIVERS.items():
        today, before = _value(record, name), _value(history[-1] if history else None, name)
        if today is None or before is None or today == before:
            continue
        typical = _typical_change([_value(r, name) for r in [*history, record]])
        size = abs(today - before) / typical if typical else abs(today - before)
        push = "riskier" if today > before else "calmer"
        moved.append((size, {"driver": driver, "text": words(today), "push": push}))
    return [d for _, d in sorted(moved, key=lambda m: -m[0])] + _events(record)


def _events(record: dict) -> list[dict]:
    """The next 5 sessions' scheduled events. M1 records null when its calendar ends inside the window (the year's
    last sessions before NSE's next-year holiday list is loaded): that is unknown, never "no event", so it is said,
    and counted riskier (unknown is caution; the contract has no neutral push)."""
    ahead = record["drivers"]["events_next_5_sessions"]
    if ahead is None:
        return [{"driver": "scheduled_event", "text": EVENTS_UNKNOWN, "push": "riskier"}]
    return [{"driver": "scheduled_event", "text": f"{EVENTS.get(e['type'], e['type'])} on {e['date']}",
             "push": "riskier"} for e in ahead]  # fmt: skip


def _value(record: dict | None, name: str) -> float | None:
    entry = (record["drivers"].get("v0_inputs") or {}).get(name) if record else None
    return entry["value"] if entry else None


def _typical_change(series: list[float | None]) -> float | None:
    """The median absolute change between consecutive sessions' values over the last 250 changes."""
    changes = [abs(b - a) for a, b in zip(series, series[1:], strict=False) if a is not None and b is not None]
    return statistics.median(changes[-WEATHER_RED_SHARE_RECORDS:]) if changes else None


def recent(inputs: WeatherInputs) -> list[dict]:
    """The last 10 sessions, the day last: each record's colour and label (live or back-fill, exploratory) and whether
    a 2% move came the next session."""
    records = {**inputs.earlier, inputs.day: inputs.record}
    days = [*inputs.sessions, inputs.day][-RECENT_SESSIONS:]
    return [{"session": d.isoformat(), "colour": colour_of(records.get(d)), "big_move": inputs.big_move.get(d),
             "label": records[d]["label"] if records.get(d) else None} for d in days]  # fmt: skip


def red_share(inputs: WeatherInputs) -> dict:
    """RED's share of the last 250 records of the basis (the day's included), as M1 counts it; over 15% is
    over-alarming, judged only once 250 such records exist."""
    label = basis(inputs)
    records = [inputs.earlier[d] for d in inputs.sessions if d in inputs.earlier] + [inputs.record]
    counted = [r["colour"] for r in records if r is not None and r["label"] == label][-WEATHER_RED_SHARE_RECORDS:]
    reds = sum(c == WeatherColour.RED for c in counted)
    share = reds / len(counted) if counted else None
    full = len(counted) == WEATHER_RED_SHARE_RECORDS
    return {"sessions": len(counted), "red_sessions": reds, "share": share, "max_share": WEATHER_RED_MAX_SHARE,
            "over_alarming": bool(full and share > WEATHER_RED_MAX_SHARE), "basis": label}  # fmt: skip


def scores(exploratory: bool) -> list[dict]:
    """G8 owns the weather's scores (`fno/forecast_scoring/v4/scores.py`) and has scored no live weather day, so each
    question and yardstick is not_enough_data with no number. A reader of G8's report replaces this once it holds
    live V6 rows; nothing here scores (judge 218)."""
    return [{"question": label, "baseline": name, "status": "not_enough_data", "n_scored": 0, "n_needed": N_NEEDED,
             "brier": None, "brier_baseline": None, "skill": None, "verdict": "not_tested", "exploratory": exploratory}
            for name in YARDSTICKS for label, _ in QUESTIONS]  # fmt: skip
