"""The weather's drivers (story M1; design 2.3): descriptive only, never an input to the probabilities or the colour.

- v0's four inputs, each with the v0 colour its value alone reaches;
- the scheduled events of the next 5 regular sessions (public rows of `events.csv`);
- the overnight US move, read only through A17b's `reading_for` (S&P 500 and Nasdaq 100 are private cues, owner
  a927390): `large` when the latest close-to-close log return is at least 2% in absolute value (V6's own 2%), else
  `normal`, `not available` when both cues read `stale` or `none`. The flag is private (orchestrator decision 72): it
  goes only to the Drive part, and the public record says "US move: private"."""

from __future__ import annotations

import math
from datetime import date

from ..forecast_v4.terms import BIG_MOVE
from ..global_cues.as_of import DECISION
from ..global_cues.reading import NONE, STALE, CueReader, reading_for
from .checklist_v0 import Event, V0Inputs, crossed
from .constants import WEATHER_US_CUES

US_PUBLIC = "private"
LARGE, NORMAL, NOT_AVAILABLE = "large", "normal", "not available"


def public_drivers(inputs: V0Inputs | None, events: list[Event] | None) -> dict:
    v0 = {}
    if inputs is not None:
        levels = crossed(inputs)
        v0 = {name: {"value": value, "reaches": str(levels[name])} for name, value in vars(inputs).items()}
    ahead = None if events is None else [{"type": e.kind, "date": e.day.isoformat()} for e in events]
    return {"v0_inputs": v0 or "not available", "events_next_5_sessions": ahead, "us_move": US_PUBLIC}


def us_move_flag(reader: CueReader | None, d: date, live_only: bool) -> str:
    """`large`, `normal` or `not available` (no reader, or every US cue `stale` or `none`)."""
    if reader is None:
        return NOT_AVAILABLE
    moves = [m for m in (_move(reader, cue, d, live_only) for cue in _us_cues(reader)) if m is not None]
    if not moves:
        return NOT_AVAILABLE
    return LARGE if any(abs(m) >= BIG_MOVE for m in moves) else NORMAL


def _us_cues(reader: CueReader) -> list[str]:
    return [cue for cue in WEATHER_US_CUES if cue in reader.tables]


def _move(reader: CueReader, cue: str, d: date, live_only: bool) -> float | None:
    """The latest usable close's log return from the close before it; None when the latest reads stale or none."""
    rows = reader.tables[cue].rows()
    source, calendar = reader.sources[cue], reader.calendars[cue]
    latest = reading_for(rows, d, DECISION, live_only, source, calendar)
    if latest.status in (STALE, NONE):
        return None
    earlier = [r for r in rows if r["value_date"] < latest.row["value_date"]]
    previous = reading_for(earlier, d, DECISION, live_only, source, calendar)
    if previous.row is None:
        return None
    return math.log(float(latest.row["value"]) / float(previous.row["value"]))
