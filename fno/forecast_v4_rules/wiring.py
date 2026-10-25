"""Composition root of protocol v4's close-based forecasters (stories G7 and G7b): the committed closes, A16's live
`rv/` rows, the A7 calendar and the record folder. Kept in this package because the v2 freeze pins every file of
`fno/forecast/` (`research/forecasts/FREEZE_v2.md`), as G4 keeps its own in `fno/forecast_scoring/`."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path

from ..config import ROOT
from ..constants import SESSION_REGULAR
from ..forecast.iv30 import PanelAtmIv30
from ..forecast_v4.eligibility import PREMIUM_WINDOW_START
from ..forecast_v4.pricing import V4_RISK_FREE_RATE
from ..forecast_v4.sessions import is_scored_session
from ..intraday.rv_table import RvTable
from ..intraday.wiring import INTRADAY_FOLDER
from ..research_data.panel_reader import read_nifty_panel
from ..research_engine.implied_vol import Black76
from ..storage.data_wiring import DATA_AREA
from ..storage.receipts import ReceiptFolder
from ..storage.wiring import PANEL_FOLDER, build_session_calendar
from . import records, series
from .capture import FORECASTERS, DayForecasts, Inputs
from .drive_records import LIVE_FOLDER
from .eod_iv30 import PANEL_OPTION_DAYS, eod_iv30_series
from .implied_backfill import FORECASTERS as IMPLIED_FORECASTERS
from .implied_backfill import ImpliedBackfill

V4_FOLDER = ROOT / "research" / "forecasts" / "v4"  # the records, G8's input (one file per forecaster and question)
CLOSES_FILE = PANEL_FOLDER / "warmup_closes.csv"  # official closes; the O6 daily index-close download extends them
METHOD_FILES = (
    "series.py",
    "baselines.py",
    "rules.py",
    "vix_rule.py",
    "capture.py",
)  # their bytes are each record's method hash
# The implied rows' own method hash: every file of this package that decides their values (the frozen G1 estimator
# `fno/forecast/iv30.py` and the protocol's `fno/forecast_v4/eligibility.py` sit outside it, hashed by their freezes)
IMPLIED_METHOD_FILES = (
    "implied.py", "eod_iv30.py", "implied_backfill.py", "drive_records.py", "series.py", "baselines.py", "records.py"
)  # fmt: skip
# Criterion 21 (judge 585's ruling): the pack-derived rows' own method hash, over every file of this package the post-
# release capture runs, from its composition root `pack_wiring.py` (a test checks the list holds that whole import
# closure inside the package). It takes in phase 1's rule files through this root too: harmless, as pack rows are
# live only and never regenerated, so a wider hash marks nothing stale
PACK_METHOD_FILES = (
    "pack_wiring.py", "wiring.py", "pack_capture.py", "pack_adapter.py", "pack_followups.py", "option_history.py",
    "v4_expiry.py", "live_quotes.py", "option_terms.py", "option_probabilities.py", "option_outcomes.py", "implied.py",
    "eod_iv30.py", "implied_backfill.py", "ratio_store.py", "intraday_series.py", "drive_records.py", "constants.py",
    "series.py", "baselines.py", "records.py", "capture.py", "rules.py", "vix_rule.py", "candle_history.py",
)  # fmt: skip
LIVE_RECORDS = f"{DATA_AREA}/{LIVE_FOLDER}"  # the pack-derived live rows (part b2)
LIVE_PATH_PARTS, JSON = 4, ".json"  # <forecaster>/<question>/<YYYY>/<date>.json under LIVE_RECORDS


def build_v4_forecasts(today: date | None = None) -> DayForecasts:
    """The forecasters on the committed closes and A16's live rows; `today` is added as a session when its close is
    not in the file yet (the live capture's day)."""
    text = CLOSES_FILE.read_text()
    rows = series.closes_rows(text)
    closes, vix = series.regular_closes(rows), series.vix_closes(rows)
    lines = [line for line in text.splitlines()[1:] if line.split(",")[1:2] == [SESSION_REGULAR]]
    calendar = build_session_calendar()
    end = max(closes[-1].day, today or closes[-1].day)
    days = [closes[0].day + timedelta(days=i) for i in range((end - closes[0].day).days + 1)]
    sessions = [d for d in days if is_scored_session(calendar, d)]
    intraday = series.live_intraday_rv(RvTable(INTRADAY_FOLDER).rows()) if INTRADAY_FOLDER.exists() else []
    return DayForecasts(Inputs(closes, vix, lines, intraday, sessions, method_sha256()))


def method_sha256(files: tuple[str, ...] = METHOD_FILES) -> str:
    """SHA-256 of the method files' bytes, carried by every record row (a back-fill made on other code is refused)."""
    package = Path(__file__).resolve().parent
    return hashlib.sha256(b"".join((package / name).read_bytes() for name in files)).hexdigest()


def implied_history() -> tuple[dict, list, list[date]]:
    """The EOD IV30 proxy on the committed A3 panel from 2024, the regular closes, and the scored sessions to the
    calendar's end (so every horizon resolves its calendar days): the history both the back-fill and the live capture
    fit their ratios on."""
    calendar = build_session_calendar()
    closes = series.regular_closes(series.closes_rows(CLOSES_FILE.read_text()))
    first = closes[0].day
    sessions = [first + timedelta(n) for n in range((calendar.last - first).days + 1)]
    sessions = [d for d in sessions if is_scored_session(calendar, d)]
    if [c.day for c in closes] != sessions[: len(closes)]:  # horizon sums go by row: one close per scored session
        raise ValueError("the closes file and A7's scored sessions disagree: fix the closes before the back-fill")
    years = range(PREMIUM_WINDOW_START.year, closes[-1].day.year + 1)
    panel = read_nifty_panel(PANEL_FOLDER, years, keep=lambda d, e: (e - d).days <= PANEL_OPTION_DAYS)
    estimator = PanelAtmIv30(Black76(), V4_RISK_FREE_RATE)  # protocol v4's own rate, never config (judge 597 SF2)
    return eod_iv30_series(sessions, lambda d: estimator.estimate(panel, d)), closes, sessions


def build_implied_backfill() -> tuple[ImpliedBackfill, date]:
    """Part b1: the exploratory V2/V3 back-fill on that history; and the last close."""
    eod, closes, sessions = implied_history()
    backfill = ImpliedBackfill(eod, series.close_proxy_rv(closes), sessions, method_sha256(IMPLIED_METHOD_FILES))
    return backfill, closes[-1].day


def first_live_implied_day(receipts: ReceiptFolder) -> date | None:
    """The earliest day with a live implied row in Drive (from its receipt's path), where the back-fill stops."""
    names = {f for f, _ in IMPLIED_FORECASTERS}
    days = []
    for found in receipts.under(LIVE_RECORDS):
        parts = found.path.removeprefix(f"{LIVE_RECORDS}/").split("/")
        if len(parts) != LIVE_PATH_PARTS or not parts[-1].endswith(JSON):
            raise ValueError(f"{found.path}: not a live record path under {LIVE_RECORDS}")
        if parts[0] in names:
            days.append(date.fromisoformat(parts[-1].removesuffix(JSON)))
    return min(days, default=None)


def v4_writer(folder: Path = V4_FOLDER):
    return lambda forecaster, question, rows: records.write(folder, forecaster, question, rows)


def record_folders() -> list[str]:
    """The repository folders `forecast-v4 capture` writes, one per forecaster id (repository-relative, ending "/"),
    so a daily run commits exactly these and never another step's files (O1, agreed 16 Oct 2026)."""
    folder = V4_FOLDER.relative_to(ROOT).as_posix()
    return [f"{folder}/{forecaster}/" for forecaster in sorted({f for f, _ in FORECASTERS})]
