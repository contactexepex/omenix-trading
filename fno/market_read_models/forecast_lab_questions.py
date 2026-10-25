"""The Forecast lab's v3 questions (story P2b; contract `FnoForecastQuestion`), mapped as agreed with the screens lead
(16 Oct 2026):

- **Yardstick:** G1's primary family is Book 2 and Book 3 each against Book 1 (protocol v1 section 8, unchanged in v2
  and v3), so `primary_baseline` is `book1_rules` and the comparisons are G4's primary rows only; a book against a
  baseline is descriptive (G4's secondary rows) and stays off this list.
- **Live only:** scores from G4's `live_1500_proxy` mode; the back-fill is the forecast history page's, labelled.
- **Verdicts:** not_tested below 40 paired days; before_review while G4 says no comparison may be called significant
  (design 12.8); only after the review better, worse or no_difference, from Holm and the sign.
- **Today:** each forecaster's own record of the session, its probability as recorded. Book 1 and the baselines are
  counted only once G4 verified the day; an AI book's status is G5's gate as G4's report gives it; a day the report
  does not reach yet, or could not verify, is pending. A forecaster that gave no forecast is left out (never
  imputed). Never sent: an AI book's reasons, its version or its session."""

from __future__ import annotations

from datetime import date

from ..constants import AI_BOOKS, BOOK1_RULES, FORECAST_Q4_VIX_UP_10D
from ..forecast.schema_v2 import ForecastRecordV2
from ..forecast.targets import PRICE_HORIZON, VIX_HORIZON
from ..forecast_scoring.score_inputs import LIVE
from .forecast_lab_forecasters import LATE_REASON
from .forecast_lab_inputs import ForecastLabInputs
from .forecast_questions import V3_QUESTIONS

N_NEEDED = 40  # protocol v1 section 8: fewer than 2L = 40 paired dates is not tested
BREACH_REASONS = ("exposed", "transcript breach")  # G5: the AI saw what it must not (prefixes of the gate's reason)
MODEL_MISMATCH = "model_mismatch"
NOT_MEASURED = {"status": "not_measured", "r": None, "projected_date": None}  # no story measures r yet


def questions(inputs: ForecastLabInputs) -> list[dict]:
    mode = _live_mode(inputs.report)
    return [_question(inputs, mode, q, contract_id, plain) for q, (contract_id, plain) in V3_QUESTIONS.items()]


def _question(inputs: ForecastLabInputs, mode: dict | None, question: str, contract_id: str, plain: str) -> dict:
    horizon = VIX_HORIZON if question == FORECAST_Q4_VIX_UP_10D else PRICE_HORIZON
    return {
        "id": contract_id, "protocol": "v3", "plain": plain, "kind": "probability", "horizon_sessions": horizon,
        "metric": "brier", "primary_baseline": BOOK1_RULES, "status": "scoring", "waiting_for": [],
        "today": _today(inputs, question, horizon), "scores": _scores(inputs.report, mode, question),
        "settle": dict(NOT_MEASURED),
    }  # fmt: skip


def _live_mode(report: dict | None) -> dict | None:
    return next((m for m in (report or {}).get("modes", []) if m["mode"] == LIVE), None)


def _today(inputs: ForecastLabInputs, question: str, horizon: int) -> dict | None:
    records = [r for r in inputs.today if r.record.question == question]
    if not records:
        return None
    values = [v for r in sorted(records, key=lambda r: r.record.book) if (v := _value(inputs, r)) is not None]
    answer_on = inputs.answer_on(inputs.day, horizon)  # None past NSE's calendar: not known yet (2.13.0)
    return {"made_on": inputs.day.isoformat(), "answer_on": answer_on.isoformat() if answer_on else None,
            "values": values}  # fmt: skip


def _value(inputs: ForecastLabInputs, record: ForecastRecordV2) -> dict | None:
    book, probability = record.record.book, record.record.probability
    if book in AI_BOOKS:
        status = _ai_status(inputs.report, inputs.day, book, probability is not None)
    else:
        status = _live_status(inputs.report, inputs.day, record.on_time) if probability is not None else None
    if status is None:
        return None
    return {"forecaster": book, "probability": probability, "variance": None, "status": status}


def _live_status(report: dict | None, day: date, on_time: bool) -> str:
    """Book 1 or a baseline: late after 15:15 IST; counted only once G4 verified the day against its capture receipt
    (a day G4 has not reached, or could not verify, is pending)."""
    if not on_time:
        return "late"
    if report is None or date.fromisoformat(report["as_of"]) < day or day.isoformat() in report["unverified_live_days"]:
        return "pending"
    return "counted"


def _ai_status(report: dict | None, day: date, book: str, said: bool) -> str | None:
    """G5's gate for the book's day as G4 reports it; None when the AI gave nothing to score (left out). A day G4 lists
    nowhere is counted only when its record holds a probability: else G4 ran before the record existed (pending)."""
    if report is None or date.fromisoformat(report["as_of"]) < day:
        return "pending"
    key = (day.isoformat(), book)
    if any((e["day"], e["book"]) == key for e in report["pending_ai_days"]):
        return "pending"
    reason = next((e["reason"] for e in report["unscored_ai_days"] if (e["day"], e["book"]) == key), None)
    if reason is None:
        return "counted" if said else "pending"
    if reason == LATE_REASON:
        return "late"
    if reason == MODEL_MISMATCH:
        return "model_mismatch"
    return "breach" if reason.startswith(BREACH_REASONS) else None


def _scores(report: dict | None, mode: dict | None, question: str) -> dict:
    rows = [s for s in (mode or {}).get("scores", []) if s["question"] == question]
    yardstick = next((s for s in rows if s["forecaster"] == BOOK1_RULES), None)
    allowed = bool((report or {}).get("confirmatory_allowed"))
    return {
        "n_scored": yardstick["primary"]["scored"] if yardstick else 0,
        "n_void": yardstick["counts"]["void"] if yardstick else 0, "n_needed": N_NEEDED,
        "per_forecaster": [{"forecaster": s["forecaster"], "n": s["primary"]["scored"],
                            "n_missing": s["counts"]["no_forecast"], "mean_loss": s["primary"]["mean_brier"]}
                           for s in rows],
        "comparisons": [_comparison(c, allowed) for c in (mode or {}).get("primary", []) if c["question"] == question],
    }  # fmt: skip


def _comparison(row: dict, allowed: bool) -> dict:
    tested = bool(row["tested"])
    return {
        "forecaster": row["first"], "baseline": row["second"], "n_pairs": row["n"],
        "mean_diff": row["mean_brier_difference"], "interval": row["interval_unadjusted_95"],
        "p_value": row["p_value"] if tested else None, "verdict": _verdict(row, tested, allowed),
        "min_effect_met": None, "futility_upper_bound": None,
    }  # fmt: skip


def _verdict(row: dict, tested: bool, allowed: bool) -> str:
    if not tested:
        return "not_tested"
    if not allowed:
        return "before_review"
    if not row["holm_significant"]:
        return "no_difference"
    return "better" if row["mean_brier_difference"] < 0 else "worse"
