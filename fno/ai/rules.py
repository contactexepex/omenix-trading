"""The rules' numbers of the day for Hybrid's input (stories F1, F5's idea, G5): the three baselines' and Book 1's
probabilities, read from the day's v2 records that the forecast-capture job wrote. The same function feeds the fire
(Hybrid's pointer) and the collection (the export Hybrid must have answered from), so both see identical numbers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..constants import FORECAST_QUESTIONS
from ..forecast.record_files import read_records_v2
from .paths import rules_path
from .pointer import RULE_FORECASTERS, Rules


class RulesMissing(RuntimeError):
    """The day's v2 records are not there or do not hold every rule forecaster's five answers."""


def rules_of_day(root: Path, day: date) -> Rules:
    path = Path(root) / rules_path(day)
    if not path.is_file():
        raise RulesMissing(f"no v2 records for {day} ({rules_path(day)})")
    found = {(r.record.question, r.record.book): r.record.probability
             for r in read_records_v2(path.read_text(encoding="utf-8")) if r.record.date == day}  # fmt: skip
    missing = [f"{b}/{q}" for q in FORECAST_QUESTIONS for b in RULE_FORECASTERS if (q, b) not in found]
    if missing:
        raise RulesMissing(f"the v2 records for {day} lack {', '.join(missing)}")
    return {q: {b: found[(q, b)] for b in RULE_FORECASTERS} for q in FORECAST_QUESTIONS}
