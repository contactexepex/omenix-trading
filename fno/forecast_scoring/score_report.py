"""Story G4's report: a stable record shape (`forecast_scores/v1`, written as `research/forecasts/scores/<as-of>.json`
for a P1-style read model, the Forecast lab) and the plain-words weekly summary for #fno-desk.

Every report says forecasts are secondary to net profit (design 12.7). No comparison is called significant before the
first scheduled review: `confirmatory_allowed` is false until six months of common-start trading of the compared books
(design 12.8); until then the primary family's Holm result is withheld (`null`) and every number is descriptive.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date

from ..constants import AI_BOOKS, BASELINE_BASE_RATE, BOOK1_RULES, FORECAST_QUESTIONS
from ..constants import ISOLATION_SEALED_SAME_DAY as ISOLATION_LABEL
from .calendar_gaps import LABEL as CALENDAR_NOTE
from .scoring import ComparisonResult, ModeScores, QuestionScores

SCHEMA = "forecast_scores/v1"
STANDING = (
    "Forecast scores are secondary to net profit: they only diagnose market reading and can never promote a book that "
    "does not make net money (design 12.7)."
)
NOT_YET = (
    "Descriptive only: no comparison is called significant before the first scheduled review, six months of "
    "common-start trading of the compared books (design 12.8)."
)
QUESTION_WORDS = dict(zip(FORECAST_QUESTIONS, (
    "NIFTY up in 20 days", "NIFTY moves 3% in 20 days", "realised vol rises", "VIX up in 10 days",
    "realised vol below implied",
), strict=True))  # fmt: skip


@dataclass(frozen=True)
class ReportContext:
    as_of: date
    inputs: dict  # provenance: file hashes, protocol commits, the scored history window
    confirmatory_allowed: bool
    late_live_records: int
    unverified_live_days: tuple[str, ...]  # live days whose files do not match their capture receipt (not scored)
    common_start: date | None = None  # first live day of all three books; coverage and the review clock start here
    coverage: dict | None = None  # book -> {counted_days, pack_days} since the common start (story G5 criterion 3)
    ai_isolation: dict[str, list[str]] = field(default_factory=dict)  # AI book -> isolation labels in its audits
    unscored_ai_days: tuple[dict, ...] = ()  # {day, book, reason}: AI days never scored
    pending_ai_days: tuple[dict, ...] = ()  # {day, book, reason}: AI days awaiting their transcript audit


def _comparison(c: ComparisonResult, allowed: bool) -> dict:
    r = c.result
    return {
        "k": c.comparison.k, "question": c.comparison.question, "first": c.comparison.first,
        "second": c.comparison.second, "n": r.n, "mean_brier_difference": r.mean_difference, "p_value": r.p_value,
        "interval_unadjusted_95": list(r.interval) if r.interval else None, "tested": r.tested,
        "holm_significant": c.holm_significant if allowed and c.comparison.primary else None,
    }  # fmt: skip


def _scores(book: str, question: str, s: QuestionScores) -> dict:
    return {"forecaster": book, "question": question, "counts": dict(s.counts), "primary": asdict(s.primary),
            "sensitivities": {name: asdict(v) for name, v in s.sensitivities.items()}}  # fmt: skip


def report_document(context: ReportContext, modes: Sequence[ModeScores]) -> dict:
    allowed = context.confirmatory_allowed
    return {
        "schema": SCHEMA,
        "as_of": context.as_of.isoformat(),
        "standing": STANDING,
        "confirmatory_allowed": allowed,
        "confirmatory_note": None if allowed else NOT_YET,
        "inputs": context.inputs,
        "late_live_records": context.late_live_records,
        "unverified_live_days": list(context.unverified_live_days),
        "common_start": context.common_start.isoformat() if context.common_start else None,
        "coverage": context.coverage,
        "ai_isolation": {**dict.fromkeys(AI_BOOKS, [ISOLATION_LABEL]), **context.ai_isolation},
        "unscored_ai_days": list(context.unscored_ai_days),
        "pending_ai_days": list(context.pending_ai_days),
        "modes": [
            {
                "mode": m.mode,
                "first_day": m.first_day.isoformat() if m.first_day else None,
                "last_day": m.last_day.isoformat() if m.last_day else None,
                "q5_flag_rate": m.q5_flag_rate,
                "scores": [_scores(book, q, s) for (book, q), s in m.scores.items()],
                "primary": [_comparison(c, allowed) for c in m.primary],
                "secondary": [_comparison(c, allowed) for c in m.secondary],
            }
            for m in modes
        ],
    }


def report_json(document: dict) -> str:
    return json.dumps(document, indent=1, sort_keys=True) + "\n"


def weekly_summary(document: dict) -> list[str]:
    """Plain words: Book 1 against the base rate on each question, per input mode, then the standing."""
    lines = [f"Omenix F&O forecasts, scores as of {document['as_of']}. {document['standing']}"]
    for mode in document["modes"]:
        lines.append(f"{mode['mode']} ({mode['first_day']} to {mode['last_day']}): Book 1 vs base rate")
        by_key = {(c["question"], c["first"], c["second"]): c for c in mode["secondary"]}
        for q in FORECAST_QUESTIONS:
            c = by_key.get((q, BOOK1_RULES, BASELINE_BASE_RATE))
            lines.append(f"- {QUESTION_WORDS[q]}: {_difference_words(c)}")
    lines += _coverage_lines(document)
    if not document["confirmatory_allowed"]:
        lines.append("Too early to tell: " + NOT_YET)
    limited = document.get("calendar_limited_days") or []  # reports before 16 Oct 2026 have no such field
    if limited:
        days = ", ".join(d["day"] for d in limited)
        lines.append(
            f"Book 1's Q1 and Q2 were the base rate alone on {len(limited)} live days ({CALENDAR_NOTE}): {days}"
        )
    if document["unverified_live_days"]:
        lines.append(
            f"Not scored (files differ from the capture receipt): {', '.join(document['unverified_live_days'])}"
        )
    return lines


def _coverage_lines(document: dict) -> list[str]:
    if not document["coverage"]:
        return ["Live coverage: no common start yet"]
    parts = [f"{book} {c['counted_days']} of {c['pack_days']}" for book, c in document["coverage"].items()]
    isolation = "; ".join(f"{book}: {', '.join(labels)}" for book, labels in document["ai_isolation"].items())
    held = f"AI book-days not scored: {len(document['unscored_ai_days'])} unscored, {len(document['pending_ai_days'])} "
    return [f"Live coverage since {document['common_start']} (days with counted forecasts of session days): "
            + ", ".join(parts), f"AI books' isolation: {isolation}", held + "pending audit"]  # fmt: skip


def _difference_words(c: dict | None) -> str:
    if c is None or not c["n"]:
        return "no paired days scored yet"
    d = c["mean_brier_difference"]
    lead = "Book 1 better" if d < 0 else "base rate better" if d > 0 else "equal"
    if not c["tested"]:
        return f"{c['n']} days, Brier difference {d:+.4f} ({lead}); too few days for an interval (40 needed)"
    low, high = c["interval_unadjusted_95"]
    return f"{c['n']} days, Brier difference {d:+.4f} ({lead}), unadjusted 95% interval {low:+.4f} to {high:+.4f}"
