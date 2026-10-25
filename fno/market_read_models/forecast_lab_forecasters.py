"""The Forecast lab's forecasters and their live coverage (story P2b; contract `FnoForecastLab.forecasters`).

- **Who:** v3's six forecasters, the three books and the three frozen baselines (G1 section 4), in plain words; the
  card's "house" forecast and the weather wait for their own sources (screens lead, 16 Oct 2026).
- **Isolation:** code for Book 1 and the baselines; an AI book's comes from G5's gate as G4's report records it, and an
  AI book is never shown as code (owner, 14 Oct 2026, condition 2).
- **Coverage (books only; G4 measures none for the baselines, so theirs is null):** pack and counted days are G4's
  own; the rest of the pack days are split by why they did not count: late (Book 1: its records generated after 15:15
  IST; an AI book: G5's reason "late"), unscored (an AI book's other gate reasons, or a live day that did not match its
  capture receipt) and missing (no forecast at all). AI days waiting for their audit are none of these. The split must
  add up to G4's pack days, else the publish stops, named and alerted (`FiguresNotComputed`), never a guessed split."""

from __future__ import annotations

from datetime import date

from ..constants import (
    AI_BOOKS,
    BASELINE_BASE_RATE,
    BASELINE_MODEL,
    BASELINE_RISK_NEUTRAL,
    BOOK1_RULES,
    BOOK2_HYBRID,
    BOOK3_AI,
    ISOLATION_SEALED_SAME_DAY,
)
from .forecast_lab_inputs import ForecastLabInputs
from .home_blocks import FiguresNotComputed

CODE, FULL_F1 = "code", "full_f1"
ISOLATION_LABELS = {ISOLATION_SEALED_SAME_DAY: "sealed same day (not full F1)", FULL_F1: "full F1"}
FORECASTERS = {  # id -> (name in plain words, kind, family)
    BOOK1_RULES: ("Rule-based (Book 1)", "family", "rule"),
    BOOK2_HYBRID: ("Hybrid: AI inside the rules (Book 2)", "family", "hybrid"),
    BOOK3_AI: ("AI (Book 3)", "family", "ai"),
    BASELINE_RISK_NEUTRAL: ("What option prices imply", "baseline", None),
    BASELINE_BASE_RATE: ("How often it happened", "baseline", None),
    BASELINE_MODEL: ("A simple statistical model", "baseline", None),
}
NO_FORECAST_REASONS = ("no_submission", "not_fired", "not_revealed")  # G5: the AI gave nothing to score
LATE_REASON = "late"
COVERAGE_BROKEN = "{book}: G4's coverage does not add up ({parts}); the Forecast lab is not built"


def forecasters(inputs: ForecastLabInputs) -> list[dict]:
    return [_forecaster(inputs, f, *spec) for f, spec in FORECASTERS.items()]


def _forecaster(inputs: ForecastLabInputs, forecaster: str, name: str, kind: str, family: str | None) -> dict:
    isolation = _isolation(inputs.report, forecaster)
    return {
        "id": forecaster, "name": name, "kind": kind, "family": family, "status": _status(inputs, forecaster),
        "isolation": isolation, "isolation_label": ISOLATION_LABELS.get(isolation),
        "coverage": _coverage(inputs, forecaster),
    }  # fmt: skip


def _status(inputs: ForecastLabInputs, forecaster: str) -> str:
    days = inputs.record_days.get(forecaster, set())
    return "running" if inputs.day in days else "not_running" if days else "not_started"


def _isolation(report: dict | None, forecaster: str) -> str:
    if forecaster not in AI_BOOKS:
        return CODE
    labels = (report or {}).get("ai_isolation", {}).get(forecaster) or [ISOLATION_SEALED_SAME_DAY]
    if len(set(labels)) != 1:  # two isolations in one book's audits: shown as the weaker one, never as full F1
        return ISOLATION_SEALED_SAME_DAY
    return labels[0]


def _coverage(inputs: ForecastLabInputs, book: str) -> dict | None:
    report = inputs.report
    counted = ((report or {}).get("coverage") or {}).get(book)
    if counted is None:
        return None
    start, as_of = date.fromisoformat(report["common_start"]), date.fromisoformat(report["as_of"])
    window = lambda d: start <= date.fromisoformat(d) <= as_of  # noqa: E731
    if book in AI_BOOKS:
        held = [e["reason"] for e in report["unscored_ai_days"] if e["book"] == book and window(e["day"])]
        pending = sum(e["book"] == book and window(e["day"]) for e in report["pending_ai_days"])
        late = sum(r == LATE_REASON for r in held)
        no_forecast = sum(r in NO_FORECAST_REASONS for r in held)
        unscored = len(held) - late - no_forecast
    else:
        late_days = {d for d in inputs.late_days.get(book, set()) if start <= d <= as_of}
        late = len(late_days)  # a late day is never also counted as unscored
        unscored = sum(window(d) and date.fromisoformat(d) not in late_days for d in report["unverified_live_days"])
        pending = 0
    missing = counted["pack_days"] - counted["counted_days"] - late - unscored - pending
    parts = {"counted": counted["counted_days"], "late": late, "unscored": unscored, "pending": pending}
    if missing < 0:
        raise FiguresNotComputed(COVERAGE_BROKEN.format(book=book, parts=parts))
    return {"pack_days": counted["pack_days"], "counted_days": counted["counted_days"], "missing_days": missing,
            "late_days": late, "unscored_days": unscored}  # fmt: skip
