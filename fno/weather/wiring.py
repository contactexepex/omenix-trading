"""Composition root of the market weather (story M1; design 2.3 names `fno/weather/wiring.py`): the committed closes
and VIX (O6), the events calendar (A6), the A7 calendar, G7's v4 record writer, A17b's cue reader for the private US
cues, and the owner's Drive for the private part."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date, timedelta
from pathlib import Path

from ..config import ROOT
from ..constants import DERIVED_AREA, SESSION_REGULAR
from ..forecast_v4.sessions import is_scored_session, next_scored_sessions
from ..forecast_v4_rules import series
from ..forecast_v4_rules.wiring import CLOSES_FILE, V4_FOLDER, v4_writer
from ..global_cues.reading import CueReader
from ..research_data.calendar import CalendarError
from ..storage import wiring as storage
from ..storage.raw_store import AreaStore, RawFileStore
from .checklist_v0 import Event, Row
from .day import WeatherDays, WeatherInputs
from .records import WeatherRecords

EVENTS_FILE = ROOT / "research" / "data" / "events" / "events.csv"
WEATHER_FOLDER = V4_FOLDER / "weather"
METHOD_FILES = (  # every file the probabilities and the colour depend on, G7's V6 outcomes and base rate included
    *(f"weather/{name}" for name in ("checklist_v0.py", "v0_live.py", "vix_scaled.py", "colour.py", "day.py")),
    "weather/constants.py",  # the thresholds and colours (moved from fno/constants.py, which was never hashed)
    "weather/wiring.py", "forecast_v4_rules/series.py", "forecast_v4_rules/baselines.py", "forecast_v4/terms.py",
    "forecast_v4/sessions.py",  # v0's event window and the previous regular session
)  # fmt: skip
HORIZON = 5  # V6b's sessions: the v0 event window of the live mode


def read_events(text: str) -> list[Event]:
    """Scheduled rows with an announcement date (as response 94's study reads them)."""
    rows = csv.DictReader(io.StringIO(text))
    return [Event(date.fromisoformat(r["date"]), r["type"], date.fromisoformat(r["announced_on"]))
            for r in rows if r["scheduled"] == "yes" and r["announced_on"]]  # fmt: skip


def build_weather_days() -> WeatherDays:
    text = CLOSES_FILE.read_text()
    rows = series.closes_rows(text)
    weather_rows = [Row(date.fromisoformat(r["date"]), float(r["underlying"]), _vix(r["vix"])) for r in rows]
    lines = [line for line in text.splitlines()[1:] if line.split(",")[1:2] == [SESSION_REGULAR]]
    calendar = storage.build_session_calendar()

    def horizon(d: date) -> date | None:
        try:
            return next_scored_sessions(calendar, d, HORIZON)[-1]
        except CalendarError:  # the calendar's last year ends inside the window: no event check
            return None

    method = method_sha256(Path(__file__).resolve().parents[1])
    return WeatherDays(WeatherInputs(weather_rows, lines, read_events(EVENTS_FILE.read_text()), horizon, method))


def method_sha256(fno: Path) -> str:
    """The SHA-256 of every file in METHOD_FILES, read under `fno` (the package folder): the record's method hash."""
    return hashlib.sha256(b"".join((fno / name).read_bytes() for name in METHOD_FILES)).hexdigest()


def _vix(text: str) -> float | None:
    return float(text) if text else None


def build_records() -> WeatherRecords:
    return WeatherRecords(WEATHER_FOLDER)


def build_writer():
    return v4_writer()


def is_session(d: date) -> bool:
    return is_scored_session(storage.build_session_calendar(), d)


def previous_regular(d: date) -> date:
    """`d-1` of the live mode: the previous regular session (a muhurat or special session never counts)."""
    calendar = storage.build_session_calendar()
    d -= timedelta(1)
    while not is_scored_session(calendar, d):
        d -= timedelta(1)
    return d


def build_cue_reader() -> CueReader | None:
    """The private US cues need the owner's Drive settings; without them, the US flag is "not available"."""
    from ..global_cues.wiring import build_reader

    try:
        return build_reader(include_private=True)
    except RuntimeError:
        return None


def build_private_store() -> RawFileStore | None:
    drive = storage.build_owner_drive()
    return None if drive is None else AreaStore(drive, DERIVED_AREA)
