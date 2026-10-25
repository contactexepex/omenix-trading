"""The forecasts section (story LR1): every number is copied from a committed report, never recomputed. Protocol v4
from G8's report JSON, with "new this week" as the difference of two reports' scored counts; protocol v1-v3 as G4's
own `weekly_summary` lines. A question G8 has not started or cannot score yet shows G8's status, never a failure. G8
scores the live and the close-proxy (back-fill) rows as two cohorts (G10); both are shown, labelled, never pooled."""

from __future__ import annotations

from ..constants import V4_COHORT_CLOSE_PROXY, V4_COHORT_LIVE
from ..forecast_scoring.score_report import weekly_summary
from ..forecast_v4.misses import MissReport
from .readers import ScoreReports
from .report import PostMortemSection
from .week import Week

NO_V4 = "Protocol v4: no G8 score report yet"
NO_G4 = "Protocol v1-v3: no G4 score report yet"
HIDDEN_SCORE_FIELDS = ("calibration",)
COHORT_LABELS = {
    V4_COHORT_CLOSE_PROXY: "close-proxy cohort (back-fill, exploratory: does not count)",
    V4_COHORT_LIVE: "live cohort",
}


class ForecastSection(PostMortemSection):
    name = "forecasts"

    def __init__(self, v4: ScoreReports, g4: ScoreReports):
        self.v4, self.g4 = v4, g4

    def lines(self, week: Week) -> list[str]:
        return ["*Forecasts*", *self._v4_lines(week), *self._g4_lines(week)]

    def data(self, week: Week) -> dict:
        v4, g4 = self.v4.latest(week.saturday), self.g4.latest(week.saturday)
        return {"v4_report": v4[0] if v4 else None, "g4_report": g4[0] if g4 else None}

    def _v4_lines(self, week: Week) -> list[str]:
        found = self.v4.latest(week.saturday)
        if found is None:
            return [NO_V4]
        path, document = found
        earlier = self.v4.latest(week.previous_saturday)
        before = _scored_counts(earlier[1]) if earlier and earlier[0] != path else None
        lines = [f"Protocol v4 (G8 report {path})"]
        for q in document["questions"]:
            lines.append(f"- {q['question']}: {q['status']}, live forecasts {q['live_forecasts']}")
            for cohort, block in _cohorts(q).items():
                lines.append(f"  {COHORT_LABELS[cohort]}:" + ("" if block["scores"] else " no rows yet"))
                lines += [f"    {name}: {_scores(s)}" for name, s in block["scores"].items()]
                lines += [f"    {_comparison((q['question'], cohort), c, before)}" for c in block["comparisons"]]
        return lines

    def _g4_lines(self, week: Week) -> list[str]:
        found = self.g4.latest(week.saturday)
        if found is None:
            return [NO_G4]
        return [f"Protocol v1-v3 (G4 report {found[0]})", *weekly_summary(found[1])]


def _cohorts(question: dict) -> dict[str, dict]:
    """G8's cohorts. A report written before G10 has one pooled block, read as the back-fill cohort: no v4 row was
    live before G10 (checked 16 Oct 2026: every v4 forecast file had 0 live rows), so its counts compare like for
    like."""
    if "cohorts" in question:
        return question["cohorts"]
    pooled = {"scores": question["scores"], "comparisons": question["comparisons"]}
    return {V4_COHORT_CLOSE_PROXY: pooled} if pooled["scores"] or pooled["comparisons"] else {}


def _scored_counts(document: dict) -> dict[tuple[str, str, str], int]:
    return {(q["question"], cohort, c["forecaster"]): c["scored"] for q in document["questions"]
            for cohort, block in _cohorts(q).items() for c in block["comparisons"]}  # fmt: skip


def _new_this_week(where: tuple[str, str], c: dict, before: dict | None) -> str:
    if before is None:
        return "first report"
    return f"new this week {c['scored'] - before.get((*where, c['forecaster']), 0)}"


def _comparison(where: tuple[str, str], c: dict, before: dict | None) -> str:
    effect = "n/a" if c["relative_improvement"] is None else f"{c['relative_improvement']:.4f}"
    counts = f"scored {c['scored']} ({_new_this_week(where, c, before)})"
    misses = MissReport(**c["misses"]).line()
    return f"{c['forecaster']} vs {c['baseline']}: {counts}, D {_number(c['mean_difference'])}, " + (
        f"relative improvement {effect}; {misses}"
    )


def _scores(scores: dict | None) -> str:
    if scores is None:
        return "no scored outcome yet"
    return ", ".join(f"{k} {_number(v)}" for k, v in scores.items() if k not in HIDDEN_SCORE_FIELDS)


def _number(value) -> str:
    return "n/a" if value is None else f"{value:.6g}" if isinstance(value, float) else str(value)
