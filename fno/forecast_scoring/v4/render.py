"""The v4 report's text and JSON (story G8). Every comparison prints its counts, D, the relative improvement against
the minimum effect, the reported p-values (never a verdict), its scored window's regime and its missed days; before
the freeze the first line says EXPLORATORY."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict

from ...constants import V4_COHORT_CLOSE_PROXY, V4_COHORT_LIVE, V4_RV_BELOW_WEEKLY_IV, V5_INSIDE_STRADDLE
from ...forecast_v4.terms import POWER_REPORT_AT
from ...forecast_v4_rules.intraday_series import INTRADAY_SERIES
from .comparison import Comparison, margin
from .days import DayCounts
from .records import EXPLORATORY
from .scoring import STATUS_SCORED, Cohort, QuestionReport

COHORT_HEADINGS = {
    V4_COHORT_CLOSE_PROXY: "close-proxy cohort (back-fill: the close stands in for the 14:30 pack; exploratory)",
    V4_COHORT_LIVE: "live cohort (captured before the cutoff)",
}  # G10: scored apart, never pooled
SERIES_NOTE = " (reported only: the intraday measure, protocol 1.1)"
QUESTION_NOTES = {  # protocol 1.4 and 1.5's own words for what V4 and V5 are, printed with them
    V4_RV_BELOW_WEEKLY_IV: " (a probabilistic diagnostic, not a variance-risk-premium estimate)",
    V5_INSIDE_STRADDLE: " (a terminal intrinsic-payoff proxy, not evidence of money)",
    **{key: SERIES_NOTE for key in INTRADAY_SERIES},
}
SECONDARY = "Forecasts are secondary to net profit; no p-value here is a verdict (verdicts come only from a look)."


def report_lines(reports: list[QuestionReport], frozen: bool, as_of: str, days: DayCounts,
                 diagnostics: Sequence[str] = ()) -> list[str]:  # fmt: skip
    lines = ([] if frozen else [EXPLORATORY]) + [f"Omenix F&O protocol v4 scores as of {as_of}", SECONDARY, days.line()]
    lines += list(diagnostics)
    for report in reports:
        lines.append(f"{report.question}: {report.status}{QUESTION_NOTES.get(report.question, '')}")
        if report.status != STATUS_SCORED:
            continue
        lines.append(f"  live forecasts: {report.live_forecasts}")
        for name, cohort in report.cohorts.items():
            lines += _cohort_lines(name, cohort)
    return lines


def _cohort_lines(name: str, cohort: Cohort) -> list[str]:
    if not cohort.scores:
        return [f"  {COHORT_HEADINGS[name]}: no rows yet"]
    lines = [f"  {COHORT_HEADINGS[name]}:"] + [f"  {f}: {_scores_text(s)}" for f, s in cohort.scores.items()]
    for comparison in cohort.comparisons:
        lines += comparison_lines(comparison)
    return lines


def comparison_lines(c: Comparison) -> list[str]:
    p = c.pairing
    counts = (f"scored {len(p.scored.differences)}, gate {len(p.gate.differences)}, unresolved {p.unresolved}, "
              f"void {p.void}, forecaster missing {p.missing_forecast}, baseline missing {p.missing_baseline}, "
              f"zero RV out of the gate {p.zero_rv_left_out_of_gate}")  # fmt: skip
    effect = "n/a" if c.relative_improvement is None else f"{c.relative_improvement:.4f}"
    hac = "n/a" if c.hac_p is None else f"{c.hac_p:.4f}"
    lines = [
        f"  {c.forecaster} vs {c.baseline}: {counts}",
        f"    D {_num(c.mean_difference)}; relative improvement {effect} (minimum {margin(c.question):g}); "
        f"p batch-means {c.batch_means_p:.4f}, studentized {c.studentized_p:.4f}, centred bootstrap "
        f"{c.centred_bootstrap_p:.4f}, HAC {hac} (reported only); halves {c.half_signs}",
        f"    {c.regime.line() if c.regime else 'no scored window'}",
        f"    {c.misses.line()}",
    ]
    if c.power is None:
        return lines + [f"    power report after {POWER_REPORT_AT} gate-set outcomes"]
    w = c.power
    return lines + [
        f"    power (planning only): r {w.r:.2f}, {w.n_required} independent outcomes needed, "
        f"{w.years_remaining:.1f} years remaining{'' if w.useful else ': cannot settle in useful time'}"
    ]


def report_json(reports: list[QuestionReport], frozen: bool, as_of: str, days: DayCounts,
                diagnostics: Sequence[str] = ()) -> dict:  # fmt: skip
    questions = [_question_json(r) for r in reports]
    return {"as_of": as_of, "exploratory": not frozen, "days": asdict(days), "questions": questions,
            "diagnostics": list(diagnostics)}  # fmt: skip


def _question_json(report: QuestionReport) -> dict:
    return {
        "question": report.question, "status": report.status, "live_forecasts": report.live_forecasts,
        "cohorts": {name: {"scores": {f: asdict(s) if s else None for f, s in c.scores.items()},
                           "comparisons": [_comparison_json(x) for x in c.comparisons]}
                    for name, c in report.cohorts.items()},
    }  # fmt: skip


def _comparison_json(c: Comparison) -> dict:
    p = c.pairing
    return {
        "forecaster": c.forecaster, "baseline": c.baseline, "scored": len(p.scored.differences),
        "gate": len(p.gate.differences), "unresolved": p.unresolved, "void": p.void,
        "missing_forecast": p.missing_forecast, "missing_baseline": p.missing_baseline,
        "zero_rv_left_out_of_gate": p.zero_rv_left_out_of_gate, "mean_difference": c.mean_difference,
        "relative_improvement": c.relative_improvement, "batch_means_p": c.batch_means_p,
        "studentized_p": c.studentized_p, "centred_bootstrap_p": c.centred_bootstrap_p, "hac_p": c.hac_p,
        "half_signs": c.half_signs, "regime": c.regime.line() if c.regime else None,
        "power": asdict(c.power) if c.power else None, "misses": asdict(c.misses),
    }  # fmt: skip


def _scores_text(scores) -> str:
    if scores is None:
        return "no scored outcome yet"
    shown = {k: v for k, v in asdict(scores).items() if k != "calibration"}
    return ", ".join(f"{k} {_num(v)}" for k, v in shown.items())


def _num(value) -> str:
    return "n/a" if value is None else f"{value:.6g}" if isinstance(value, float) else str(value)
