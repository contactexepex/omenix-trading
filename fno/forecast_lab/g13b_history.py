"""G13b's scored forecasts as the page's history (story FL1-1c): G13b's own score rows, never recomputed, each with
the band it scored, from G13b's live records (sealed) and back-fill records, read through G13b's reader. For one
method, horizon and target day a live row wins over the 3 pm back-fill, which wins over the end-of-day back-fill, so
live points replace history as they accrue and nothing counts twice. Only the current method version counts (the one
behind the newest record, live first): two versions are never pooled, and a band is paired only with its own
version's score (judge 434)."""

from __future__ import annotations

from datetime import date

from .page.history import HistorySource, ScorePoint
from .page.model import Band

LIVE, BACKFILL_3PM, BACKFILL_EOD = "live", "backfill_3pm", "backfill_eod"
PREFERENCE = {LIVE: 0, BACKFILL_3PM: 1, BACKFILL_EOD: 2}


def _band(row: dict) -> Band | None:
    if row.get("q50") is None:
        return None
    return Band(row["q05"], row["q25"], row["q50"], row["q75"], row["q95"])


class G13bHistory(HistorySource):
    def __init__(self, forecasts, scores):
        """`forecasts`: G13b's `RangeForecasts`; `scores`: its `RangeScores`."""
        self.forecasts, self.scores = forecasts, scores

    def _records(self, underlying: str) -> list[dict]:
        live = [s.record for s in self.forecasts.live()]
        return [r for r in live + list(self.forecasts.backfill()) if r["underlying"] == underlying]

    @staticmethod
    def _current(records: list[dict]) -> str | None:
        """The method version of the newest record; a live record wins over a back-fill of the same day."""
        newest = max(records, key=lambda r: (r["day"], -PREFERENCE.get(r["label"], len(PREFERENCE))), default=None)
        return newest["method_sha256"] if newest else None

    @staticmethod
    def _bands(records: list[dict], method: str | None) -> dict[tuple[str, str, str], dict]:
        """(label, issue day, issue) -> the current version's rows by (forecaster, horizon)."""
        return {(r["label"], r["day"], r["issue"]): {(row["forecaster"], row["horizon"]): row for row in r["rows"]}
                for r in records if r["method_sha256"] == method}  # fmt: skip

    def targets(self, underlying: str, method: str, horizon: str) -> set[date]:
        records = self._records(underlying)
        version = self._current(records)
        return {date.fromisoformat(row["target_day"]) for r in records if r["method_sha256"] == version
                for row in r["rows"] if (row["forecaster"], row["horizon"]) == (method, horizon)
                and row.get("status") == "ok" and row.get("target_day")}  # fmt: skip

    def points(self, underlying: str) -> list[ScorePoint]:
        records = self._records(underlying)
        method = self._current(records)
        bands, chosen = self._bands(records, method), {}
        for row in self.scores.rows(underlying):
            if row["label"] not in PREFERENCE or row["method_sha256"] != method:
                continue
            key = (row["forecaster"], row["horizon"], row["target_day"])
            if key in chosen and PREFERENCE[chosen[key]["label"]] <= PREFERENCE[row["label"]]:
                continue
            chosen[key] = row
        out = []
        for row in chosen.values():
            issue = bands.get((row["label"], row["issue_day"], row["issue"]), {})
            scored = issue.get((row["forecaster"], row["horizon"]))
            out.append(ScorePoint(row["forecaster"], row["horizon"], date.fromisoformat(row["target_day"]),
                                  row["outcome_close"], row["quantile_score"] * row["outcome_close"],
                                  row["inside_25_75"], row["inside_05_95"], row["label"] == LIVE,
                                  date.fromisoformat(row["issue_day"]), _band(scored) if scored else None))  # fmt: skip
        return sorted(out, key=lambda p: (p.method, p.horizon, p.target_day))
