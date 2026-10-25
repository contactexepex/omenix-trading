"""The card's forecast section (story T1 v1): the house forecast per question from the latest committed live G1
capture on or before the card's day, with its scored track record (`TrackRecords`).

The house forecast is the past average (`baseline_b_base_rate`) on all five questions (orchestrator, 15 Oct 2026):
G1 v1-v3 name no primary yardstick for any question, and the base rate is the only baseline defined on all five, with no
model or market input ("baselines until something passes", REPLAN). It was never chosen by its scores. It is a
display choice only and changes no scoring. The other forecasters are counted on the card; their full list belongs on
the dashboard. Protocol v4's forecasters and its own primary baselines (G6, design 05 section 5.3) plug in later as
another `ForecastSource`."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

from ..constants import BASELINE_BASE_RATE, FORECAST_QUESTIONS
from ..forecast.record_files import read_records_v2
from ..forecast.schema_v2 import GENERATION_DEADLINE, ForecastRecordV2
from ..models import IST
from .committed import CommittedRecords
from .sections import CardSection, ForecastSource, UsedRecord
from .track_record import TrackRecords

LIVE_FOLDER = "research/forecasts/live_v2"  # G3's live capture, `<YYYY>/<d>_forecasts.csv`
SCORES_FOLDER = "research/forecasts/scores"  # G4's reports, `<d>.json`
CAPTURE_FILE = re.compile(r"(\d{4}-\d{2}-\d{2})_forecasts\.csv")
REPORT_FILE = re.compile(r"(\d{4}-\d{2}-\d{2})\.json")
QUESTION_NAMES = dict(zip(FORECAST_QUESTIONS, (
    "NIFTY higher in 20 sessions", "NIFTY moves 3% or more in 20 sessions",
    "20-day realised volatility rises above the last 20 days'", "India VIX higher in 10 sessions",
    "20-day realised volatility below today's 30-day implied volatility",
)))  # fmt: skip
NONE_YET = "Forecasts: none on record yet"
HEADER = "Forecasts on record: live capture of {day}{age}; track records from the score report of {report}"
OLDER = " (not today's: the latest committed capture)"
LATE = "This capture was generated at {at} IST, after its {deadline:%H:%M} deadline: its records are not scored"
HOUSE_NOTE = "House forecast ({house}): no primary named in G1; past average shown (orchestrator's fallback rule)."
OTHERS = "{count} other forecasters recorded; none has passed its test yet. None of this is advice."
QUESTION_LINE = "{question} ({name}): past average {probability:.2f} | {record}"
NO_FORECAST = "{question} ({name}): past average gave no forecast"
NOT_IN_CAPTURE = "{question} ({name}): no past-average record in this capture"
LATE_MISSING = "scored live forecasts for {day} (the capture was late)"


def _latest(names: list[str], pattern: re.Pattern, day: date) -> date | None:
    days = [date.fromisoformat(m.group(1)) for m in map(pattern.fullmatch, names) if m]
    return max((d for d in days if d <= day), default=None)


class LiveCaptureForecasts(ForecastSource):
    def __init__(
        self, records: CommittedRecords, house: str = BASELINE_BASE_RATE, live_folder: str = LIVE_FOLDER,
        scores_folder: str = SCORES_FOLDER,
    ):  # fmt: skip
        self.records, self.house, self.live_folder, self.scores_folder = records, house, live_folder, scores_folder

    def forecasts(self, day: date) -> CardSection:
        capture = self._latest_capture(day)
        if capture is None:
            return CardSection("forecasts", (NONE_YET,), missing=(f"live forecast capture on or before {day}",))
        path, capture_day, data = capture
        rows = read_records_v2(data.decode("utf-8"))  # an unreadable capture fails the section, which says so
        used, missing = [UsedRecord.of(path, data)], []
        report_day, records = self._track_records(day, used, missing)
        house = [r.record for r in rows if r.record.book == self.house]
        others = len({r.record.book for r in rows} - {self.house})
        late = _late_lines(rows)
        missing += [LATE_MISSING.format(day=capture_day)] if late else []
        lines = [HEADER.format(day=capture_day, age=OLDER if capture_day < day else "", report=report_day or "none")]
        lines += late + [HOUSE_NOTE.format(house=self.house), OTHERS.format(count=others)]
        lines += _question_lines(house, records, missing)
        return CardSection("forecasts", tuple(lines), tuple(used), tuple(missing))

    def _latest_capture(self, day: date) -> tuple[str, date, bytes] | None:
        years = sorted(
            (y for y in self.records.names(self.live_folder) if y.isdigit() and int(y) <= day.year), reverse=True
        )
        for year in years:
            found = _latest(self.records.names(f"{self.live_folder}/{year}"), CAPTURE_FILE, day)
            data = self.records.read(f"{self.live_folder}/{year}/{found}_forecasts.csv") if found else None
            if data is not None:
                return f"{self.live_folder}/{year}/{found}_forecasts.csv", found, data
        return None

    def _track_records(self, day: date, used: list, missing: list) -> tuple[str | None, TrackRecords]:
        """The latest score report dated before the card's day (a same-day report may hold that day's later data)."""
        found = _latest(self.records.names(self.scores_folder), REPORT_FILE, day - timedelta(days=1))
        path = f"{self.scores_folder}/{found}.json"
        data = self.records.read(path) if found else None
        if data is None:
            missing.append(f"forecast score report dated before {day}")
            return None, TrackRecords(None)
        try:
            records = TrackRecords(json.loads(data))
        except (ValueError, KeyError, TypeError) as error:
            missing.append(f"{path}: not readable ({type(error).__name__})")
            return None, TrackRecords(None)
        used.append(UsedRecord.of(path, data))
        return found.isoformat(), records


def _late_lines(rows: list[ForecastRecordV2]) -> list[str]:
    late = sorted({r.generated_at.astimezone(IST).strftime("%H:%M") for r in rows if not r.on_time})
    return [LATE.format(at=", ".join(late), deadline=GENERATION_DEADLINE)] if late else []


def _question_lines(house_rows: list, records: TrackRecords, missing: list) -> list[str]:
    lines = []
    for question in FORECAST_QUESTIONS:
        named = {"question": question, "name": QUESTION_NAMES[question]}
        asked = [r for r in house_rows if r.question == question]
        if not asked:
            lines.append(NOT_IN_CAPTURE.format(**named))
            missing.append(f"past average for {question} not in the capture")
        for r in asked:
            if r.probability is None:
                lines.append(NO_FORECAST.format(**named))
            else:
                record = records.line(r.book, question, r.probability)
                lines.append(QUESTION_LINE.format(**named, probability=r.probability, record=record))
    return lines
