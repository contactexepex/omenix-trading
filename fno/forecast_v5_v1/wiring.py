"""Composition root of story G14: v4's inputs (`forecast_v4_rules.wiring`), A16b's candle history through W8's one
reader (`pack_wiring.candle_history`), A16's live rows, G7b's one pairing, the record folder and the freeze records."""

from __future__ import annotations

from datetime import date

from ..config import ROOT
from ..constants import V1_RV_1S
from ..forecast_v4_rules.candle_history import paired_rv
from ..forecast_v4_rules.pack_wiring import candle_history, candle_rv, live_rv
from ..forecast_v4_rules.wiring import build_v4_forecasts
from . import records
from .capture import FORECASTERS, V5Day, Writer
from .history import from_candle
from .method import method_sha256
from .report import render, score

V5_FOLDER = ROOT / "research" / "forecasts" / "v5"
RECORDS_FOLDER = V5_FOLDER / "v1_candle"  # <forecaster>/v1_rv_next_session.csv
FREEZE_FILE = V5_FOLDER / "FREEZE_v5_v1.md"
V4_FREEZE_FILE = ROOT / "research" / "forecasts" / "FREEZE_v4.md"


def build_day(d: date) -> V5Day:
    return V5Day(build_v4_forecasts(d).inputs, from_candle(candle_history()), d, method_sha256(ROOT))


def writer() -> Writer:
    return lambda rows: records.write_day(RECORDS_FOLDER, V1_RV_1S, rows)


def build_report() -> list[str]:
    """Every forecaster's live rows scored against A16's live RV (`live_rv`, never the candle table), then the
    measure-gap table."""
    live = live_rv()
    sessions = build_v4_forecasts().inputs.sessions
    rows = {name: records.read(records.path(RECORDS_FOLDER, name, V1_RV_1S)) for name in FORECASTERS.values()}
    scores = [score(name, rows[name], live, sessions) for name in FORECASTERS.values()]
    return render(scores, paired_rv(live, candle_rv()))


def record_folders() -> list[str]:
    """The repository folders the capture writes, one per forecaster, for O1's pathspecs."""
    folder = RECORDS_FOLDER.relative_to(ROOT).as_posix()
    return [f"{folder}/{name}/" for name in sorted(FORECASTERS.values())]
