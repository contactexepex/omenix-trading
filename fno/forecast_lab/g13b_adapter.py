"""G13b's reader into FL1's `RangeSource` port (agreed with the G13 builder, 21 Oct 2026). G13b keeps its concrete
reader (`fno/price_ranges/reader.py`: `RangeForecasts`, `RangeScores`, `Outcomes`); this one class maps its records
and score rows, so a change on either side touches only this file."""

from __future__ import annotations

from datetime import date

from .constants import LEVELS
from .ranges import Outcomes, RangeRow, RangeScore, RangeSource, SealedIssue


def _day(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


def _row(row: dict) -> RangeRow | None:
    """A record row; one without a target day (G13b: not_eligible, the calendar ends first) is left out."""
    target = _day(row.get("target_day"))
    if target is None:
        return None
    quantiles = {level: row[f"q{round(level * 100):02d}"] for level in LEVELS} if row.get("q50") is not None else {}
    return RangeRow(row["forecaster"], row["horizon"], target, quantiles, row.get("p_up"), row["status"],
                    row.get("reason") or "")  # fmt: skip


def _score(row: dict) -> RangeScore:
    return RangeScore(row["forecaster"], row["horizon"], row["issue"], _day(row["issue_day"]), _day(row["target_day"]),
                      row["outcome_close"], row["quantile_score"], row["inside_25_75"], row["inside_05_95"],
                      row.get("brier_up"), row.get("method_sha256") or "")  # fmt: skip


class G13bRanges(RangeSource):
    def __init__(self, forecasts, scores):
        """`forecasts`: G13b's `RangeForecasts`; `scores`: its `RangeScores`."""
        self.forecasts, self.score_reader = forecasts, scores

    def sealed(self, underlying: str, day: date, issue: str) -> SealedIssue | None:
        found = self.forecasts.sealed(underlying, day, issue)
        if found is None:
            return None
        record = found.record
        rows = tuple(r for r in (_row(row) for row in record.get("rows", [])) if r is not None)
        return SealedIssue(underlying, day, issue, record["s_ref"], found.sealed_at, rows, found.late)

    def scores(self, underlying: str, target_day: date) -> list[RangeScore]:
        rows = self.score_reader.rows(underlying)
        return [_score(r) for r in rows if _day(r["target_day"]) == target_day]

    def scored_days(self, underlying: str, through: date) -> list[date]:
        return list(self.score_reader.scored_days(underlying, through))

    def history(self, underlying: str, through: date) -> list[RangeScore]:
        return [
            _score(r) for r in self.score_reader.rows(underlying, live_only=True) if _day(r["target_day"]) <= through
        ]


class G13bCloses(Outcomes):
    def __init__(self, outcomes):
        """`outcomes`: G13b's `closes.Outcomes` (NSE's official index closes)."""
        self.outcomes = outcomes

    def close(self, underlying: str, day: date) -> float | None:
        return self.outcomes.close(underlying, day)
