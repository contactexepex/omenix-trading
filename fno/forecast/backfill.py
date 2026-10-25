"""The history back-fill for evaluation (stories G2 and G3): the three baselines' and Book 1's forecasts on every
panel trading day, as forecast records (frozen schema), labelled "close proxy" (history uses the day's close for its
15:00 values; PROTOCOL.md section 1).

Every record's `method_or_version` names the method and version, `close-proxy`, and the day's IV30 state
(`iv30:interpolated`, `iv30:flagged` or `iv30:none`), so the flag travels with the forecast (the frozen schema has no
column for it); Book 1's also carries its method file's SHA-256. `pack_sha256` is the panel manifest's SHA-256.
Written by `record_files.records_gzip` (fixed bytes for the same records).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, time
from typing import Protocol

from ..constants import BOOK1_RULES, FORECAST_QUESTIONS, SESSION_MUHURAT
from ..models import IST
from .baselines import Probabilities
from .book1_method import book1_probabilities, method_label
from .history import ForecastHistory
from .schema import ForecastRecord

BACKFILL_FILE = "research/forecasts/backfill/backfill_v1.csv.gz"
BASELINE_VERSION = "v1"
CLOSE_PROXY = "close-proxy"
CLOSE_TIME = time(15, 30)  # history's values are the day's closes


class Forecaster(Protocol):
    """What the back-fill needs from a baseline: its name and its probabilities on a day."""

    name: str

    def probabilities(self, day: date) -> Probabilities: ...


def iv30_state(history: ForecastHistory, day: date) -> str:
    iv30 = history.iv30(day)
    return "iv30:none" if iv30 is None else "iv30:flagged" if iv30.flagged else "iv30:interpolated"


def forecast_days(history: ForecastHistory) -> list[date]:
    """Trading days with option rows in the panel (the warm-up sessions give closes only)."""
    calendar, options = history.calendar, history.panel.options
    return [d for d in history.days if d in options and calendar.session_kind(d) != SESSION_MUHURAT]


def _records(book: str, day: date, label: str, values: Mapping[str, float | None], pack: str) -> list[ForecastRecord]:
    cutoff = datetime.combine(day, CLOSE_TIME, tzinfo=IST)
    return [ForecastRecord(book, day, cutoff, q, values.get(q), label, pack) for q in FORECAST_QUESTIONS]


def backfill_records(history: ForecastHistory, baselines: Iterable[Forecaster], pack: str) -> list[ForecastRecord]:
    baselines, book1 = list(baselines), method_label()
    records: list[ForecastRecord] = []
    for day in forecast_days(history):
        state = iv30_state(history, day)
        by_baseline = {b.name: b.probabilities(day) for b in baselines}
        for name, values in by_baseline.items():
            records += _records(name, day, f"{name}/{BASELINE_VERSION}/{CLOSE_PROXY}/{state}", values, pack)
        records += _records(BOOK1_RULES, day, f"{book1}/{CLOSE_PROXY}/{state}", book1_probabilities(by_baseline), pack)
    return records
