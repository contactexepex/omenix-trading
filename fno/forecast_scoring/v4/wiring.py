"""Composition root of story G8 (protocol v4 scoring): G7's forecast files, G7's series rules for outcomes, the frozen
threshold tools, the look records, the slot registrations and (G10 completion, criterion 6) the day labels: the release
records read from Drive through O9's verified cache plus the one rule for a day without a record. Swapping any of them
is one class plus one line here."""

from __future__ import annotations

from datetime import date
from functools import cache

from ...config import ROOT
from ...constants import V4_PACK_LIVE_KEY
from ...forecast_v4.sessions import is_scored_session
from ...intraday.rv_table import RvTable
from ...v4_pack.paths import DAYS_FOLDER, DEADLINES_FOLDER
from .cutoff_moves import RecordedCutoffMoves
from .days import DayCounts, LateDaysOut, LiveDayLabels, day_counts
from .deadlines import DeadlineVerdicts, LateCommitmentsOut, unchecked_days
from .drive_forecasts import CombinedForecasts, DriveForecastRecords, chosen_paths
from .g7_series import G7Series, StoredOptionOutcomes
from .inputs import ForecastFiles
from .outcomes import SeriesOutcomes
from .primary import primary_values
from .reconcile import AiSlotDays, sessions_not_late
from .records import LookRecords, SlotRegistry
from .release_days import ReleasedDays
from .scoring import V4Scoring
from .slot_file import SlotFile
from .thresholds import FrozenToolThresholds

FORECASTS_FOLDER = ROOT / "research" / "forecasts" / "v4"  # G7's files (agreed layout)
SCORES_FOLDER = ROOT / "research" / "forecasts" / "v4_scores"
FREEZE_FILE = ROOT / "research" / "forecasts" / "FREEZE_v4.md"
SLOTS_FILE = ROOT / "research" / "forecasts" / "v4_slots.csv"  # the slot registrations (response 287)
CLOSES_FILE = ROOT / "research" / "data" / "nifty-panel" / "warmup_closes.csv"  # O6
INTRADAY_FOLDER = ROOT / "research" / "data" / "intraday"  # A16's live rv/ files (never A16b's rv-candle/)


def build_scoring() -> V4Scoring:
    """The slots registered in `v4_slots.csv` (none before the freeze commit writes them). A system_late day is
    out of the forecasts and the outcomes for every forecaster (G10)."""
    inputs = LateDaysOut(_checked_forecasts(), _outcomes(), build_day_labels(_today()))
    return V4Scoring(inputs, inputs, build_slot_registry())


def build_ai_slot_days() -> AiSlotDays:
    sessions = sessions_not_late(_is_session(), build_day_labels(_today()))
    return AiSlotDays(ForecastFiles(FORECASTS_FOLDER), build_slot_registry(), sessions)


def build_day_counts(as_of: date) -> DayCounts:
    flags = RecordedCutoffMoves(RvTable(INTRADAY_FOLDER).rows())  # A16's 15:30 run commits each day's flag
    labels = build_day_labels(as_of)
    unchecked = [day for day in build_unchecked_days() if day <= as_of]
    return day_counts(labels.labels(), flags.moved, as_of, labels.pending(), len(unchecked))


def build_unchecked_days() -> list[date]:
    """The live days with a row whose 15:10 deadline has no verdict yet (a recorded look refuses while one exists)."""
    from ...constants import V4_DAY_SYSTEM_LATE
    from .scoring import QUESTIONS

    late = {d for d, label in build_day_labels(_today()).labels().items() if label.label == V4_DAY_SYSTEM_LATE}
    return [day for day in unchecked_days(_checked_forecasts(), QUESTIONS) if day not in late]  # out for everyone


def _checked_forecasts() -> LateCommitmentsOut:
    """G7's and M1's files and G7b's Drive records with the 15:10 verdicts applied: a late live row is no forecast
    that day."""
    return LateCommitmentsOut(_forecasts(), DeadlineVerdicts(build_drive_records(DEADLINES_FOLDER)))


def build_drive_records(folder: str):
    """The one seam to the v4 records in Drive (a folder, or one receipted file, inside the data area): G10's day
    labels and deadline verdicts and G7b's records all read through it, so a test replaces it once."""
    from ...storage.data_wiring import DATA_AREA, build_drive_cache, receipt_folder
    from .drive_records import DriveRecords

    return DriveRecords(receipt_folder(), build_drive_cache, DATA_AREA, folder)


def build_day_labels(today: date) -> LiveDayLabels:
    """The one day source of the three readers above: Drive's release records, and `missing_label` for the rest, from
    the pack's live date (the release's catch-up starts there too)."""
    from ...config import load_config
    from ...v4_pack.sessions import sessions_between

    records = ReleasedDays(build_drive_records(DAYS_FOLDER))
    return LiveDayLabels(records, sessions_between(_is_session()), label_start(load_config()), today)


def label_start(cfg: dict) -> date | None:
    """The first session with a day label: `daily.live_from.v4_pack` (D2 revised, 24 Oct: a day before the pack was
    live had no pack to release, so it has no label and its live rows stay in)."""
    from ...daily.wiring import live_dates

    return live_dates(cfg)[V4_PACK_LIVE_KEY]


def _is_session():
    from ...storage.wiring import build_session_calendar

    calendar = build_session_calendar()
    return lambda d: is_scored_session(calendar, d)


def _today() -> date:
    from ...models import now_ist

    return now_ist().date()


def build_look_records() -> LookRecords:
    return LookRecords(SCORES_FOLDER, FREEZE_FILE)


def build_freeze_check():
    """Protocol v4's freeze check on this tree (`freeze_check.check`); before the record exists, nothing to check (the
    outputs are exploratory)."""
    from ...research_engine.ledger import Git
    from .freeze_check import FreezeCheck, check

    if not FREEZE_FILE.is_file():
        return FreezeCheck()
    return check(ROOT, FREEZE_FILE.read_text(encoding="utf-8"), Git(ROOT))


def build_thresholds() -> FrozenToolThresholds:
    return FrozenToolThresholds(ROOT / "tools")


@cache
def _forecasts() -> CombinedForecasts:
    """G7's repository CSVs and G7b's records kept in Drive (G7b completion, part e), built once per command: every
    live record and this code's latest back-fill per forecaster and question, chosen from the receipts and fetched
    verified through `build_drive_records`. With no such receipt the Drive source is left out (no Drive access)."""
    from ...forecast_v4_rules.drive_records import BACKFILL_FOLDER, LIVE_FOLDER
    from ...forecast_v4_rules.wiring import IMPLIED_METHOD_FILES, method_sha256
    from ...storage.data_wiring import DATA_AREA

    area = f"{DATA_AREA}/"
    method = method_sha256(IMPLIED_METHOD_FILES)
    receipted = [p.removeprefix(area) for f in (LIVE_FOLDER, BACKFILL_FOLDER) for p in build_drive_records(f).paths()]
    chosen = chosen_paths(receipted, method)
    if not chosen:
        return CombinedForecasts([ForecastFiles(FORECASTS_FOLDER)])
    files = {path.removeprefix(area): data for c in chosen for path, data in build_drive_records(c).files().items()}
    return CombinedForecasts([ForecastFiles(FORECASTS_FOLDER), DriveForecastRecords(files, method)])


def _outcomes() -> SeriesOutcomes:
    """G7's series rules, and V4's and V5's outcomes from G7b's stored records (part e)."""
    from ...forecast_v4_rules.pack_wiring import option_history

    rv = RvTable(INTRADAY_FOLDER)
    history = option_history(_scored_sessions())
    return SeriesOutcomes(G7Series(CLOSES_FILE.read_text(encoding="utf-8"), rv.rows), StoredOptionOutcomes(history))


def _scored_sessions() -> list[date]:
    from datetime import timedelta

    from ...storage.wiring import build_session_calendar

    calendar = build_session_calendar()
    days = (calendar.first + timedelta(n) for n in range((calendar.last - calendar.first).days + 1))
    return [d for d in days if is_scored_session(calendar, d)]


def build_diagnostic_lines() -> list[str]:
    """The report's descriptive lines (G7b completion, part e): the pack / EOD IV30 drift from G7b's stored pairs,
    W8's back-fill / live and W3's intraday / close-proxy `RV_s` from the committed A16 and A16b tables."""
    from ...forecast_v4_rules import series
    from ...forecast_v4_rules.candle_history import drift_days, paired_rv
    from ...forecast_v4_rules.pack_followups import DRIFT_FOLDER, drift_pair
    from ...forecast_v4_rules.pack_wiring import candle_rv, live_rv
    from .diagnostic_lines import diagnostic_lines

    drift = [drift_pair(data) for data in build_drive_records(DRIFT_FOLDER).files().values()]
    live = live_rv()
    closes = series.regular_closes(series.closes_rows(CLOSES_FILE.read_text(encoding="utf-8")))
    close_rv = {v.day: v.value for v in series.close_proxy_rv(closes)}
    level = [(day, value, close_rv.get(day)) for day, value in live.items() if value is not None]
    return diagnostic_lines(drift, drift_days(paired_rv(live, candle_rv())), level)


def build_slot_registry() -> SlotRegistry:
    """One registry for scoring and the look's reconciliation: the committed slot registrations (none before the
    freeze commit writes the first rows)."""
    return SlotFile(SLOTS_FILE, _first_eligible, _frozen_on)


def _frozen_on() -> date | None:
    records = build_look_records()
    return records.frozen_on() if records.frozen() else None


def _first_eligible(question: str) -> date | None:
    """The first live session after the freeze with a value of the question's primary baseline (None before the
    freeze, or while there is none)."""
    records = build_look_records()
    if not records.frozen():
        return None
    after = records.frozen_on()
    values = primary_values(question, _forecasts())
    return min((d for d, v in values.items() if v.live and v.value is not None and d > after), default=None)
