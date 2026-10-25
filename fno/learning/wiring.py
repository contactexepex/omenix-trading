"""Composition root of the weekly post-mortem (story LR1; design 4.3 names `fno/learning/wiring.py`): the committed G4
and G8 reports, M1's weather records, G7's V6a outcome rule, the 3 pm capture markers, T1's delivery files, A16's rv
table, the A7 calendar, the alert sender, the post-mortem routine's trigger (two repository secrets) and BG1's signal.
Another source or advocate is one new class and one line here."""

from __future__ import annotations

import os
from datetime import date

from ..advocate.routine_file import RoutineFileAdvocate
from ..cards.committed import GitHeadRecords
from ..cards.deliveries import RepoDeliveryFiles
from ..composition import build_alert_sender
from ..config import ROOT
from ..constants import ENV_ROUTINE_POSTMORTEM_TOKEN, ENV_ROUTINE_POSTMORTEM_TRIGGER_ID, V6_BIG_MOVE_1S
from ..forecast_scoring.v4.wiring import INTRADAY_FOLDER, SCORES_FOLDER, build_look_records
from ..forecast_scoring.wiring import SCORES_FOLDER as G4_SCORES_FOLDER
from ..forecast_v4.terms import HORIZON_SESSIONS
from ..forecast_v4_rules import series
from ..forecast_v4_rules.wiring import CLOSES_FILE
from ..intraday.rv_table import RvTable
from ..models import now_ist
from ..pipeline.trigger import RoutineFireTrigger, RoutineTrigger, UnconfiguredTrigger
from ..quotes.recorder import DATASET
from ..storage.wiring import build_session_calendar
from ..weather.wiring import build_records as build_weather_records
from .forecast_section import ForecastSection
from .health_section import DataHealthSection
from .publish import Publisher
from .readers import CaptureMarkers, IntradaySessions, ReportFolder
from .report import PostMortemBuilder, PostMortemRecords
from .weather_section import WeatherSection
from .week import Week, build_week
from .writer import PostMortemRoutine, SignalFile

POSTMORTEM_FOLDER = ROOT / "research" / "postmortems"
QUOTES_FOLDER = ROOT / "research" / "data" / "quotes" / DATASET
ROUTINE_NAME = "weekly post-mortem"


def week_of(saturday: date) -> Week:
    return build_week(build_session_calendar(), saturday)


def build_records() -> PostMortemRecords:
    return PostMortemRecords(POSTMORTEM_FOLDER)


def build_builder() -> PostMortemBuilder:
    weather = build_weather_records()
    sections = (
        ForecastSection(ReportFolder(SCORES_FOLDER, "research/forecasts/v4_scores"),
                        ReportFolder(ROOT / G4_SCORES_FOLDER, G4_SCORES_FOLDER)),
        WeatherSection(weather, _big_move_next),
        DataHealthSection(CaptureMarkers(QUOTES_FOLDER), RepoDeliveryFiles(ROOT, GitHeadRecords(ROOT)),
                          lambda d: weather.for_day(d) is not None, IntradaySessions(RvTable(INTRADAY_FOLDER).rows)),
    )  # fmt: skip
    return PostMortemBuilder(sections, build_look_records().frozen)


def _big_move_next() -> dict[date, bool]:
    closes = series.regular_closes(series.closes_rows(CLOSES_FILE.read_text(encoding="utf-8")))
    return {o.day: o.value for o in series.big_move_outcomes(closes, HORIZON_SESSIONS[V6_BIG_MOVE_1S])}


def build_trigger(env=os.environ) -> RoutineTrigger:
    names = (ENV_ROUTINE_POSTMORTEM_TRIGGER_ID, ENV_ROUTINE_POSTMORTEM_TOKEN)
    trigger_id, token = (env.get(n) for n in names)
    if not (trigger_id and token):
        return UnconfiguredTrigger(ROUTINE_NAME, tuple(n for n in names if not env.get(n)))
    return RoutineFireTrigger(ROUTINE_NAME, trigger_id, token)


def build_routine(env=os.environ) -> PostMortemRoutine:
    return PostMortemRoutine(build_trigger(env), build_records(), SignalFile(ROOT), now_ist)


def build_publisher() -> Publisher:
    return Publisher(build_records(), RoutineFileAdvocate(), build_alert_sender())
