"""Forecast scoring (story G4; protocol v1 sections 7 and 8, unchanged by v2): each forecaster's scores per question and
the comparisons, per input mode (history `close_proxy` and live `live_1500_proxy` are never mixed).

A forecast is scored only when its outcome is resolved and not void (`resolution.py`), never earlier. Per forecaster
and question: forecasts, "no forecast", pending, void and scored counts; mean Brier, mean log score and calibration.
Question 5 on flagged-IV30 days is a separate descriptive sensitivity; baseline (a) on questions 1 and 2 is also split
into flagged and unflagged IV30 days. Comparisons: the primary family (10 tests, Books 2 and 3 against Book 1, Holm) and
the secondary, descriptive ones (effect sizes with unadjusted 95% intervals). No comparison is called significant
before the first scheduled review (design 12.8: six months of common-start trading of the compared books).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from ..constants import BASELINE_RISK_NEUTRAL, FORECAST_Q1_UP_20D, FORECAST_Q2_MOVE_3PCT_20D, FORECAST_Q5_RV_BELOW_IV
from ..forecast.comparisons import Comparison, primary_family, secondary_comparisons
from .block_bootstrap import BootstrapResult, compare, holm_significant
from .resolution import PENDING, RESOLVED, VOID, OutcomeResolver, Resolution
from .score_inputs import ScoredForecast
from .scores import ScoreSummary, brier, summarise

FLAGGED = "flagged"
NO_FORECAST = "no_forecast"


@dataclass
class QuestionScores:
    """One forecaster's counts and scores on one question in one input mode."""

    counts: dict[str, int] = field(default_factory=lambda: {"forecasts": 0, NO_FORECAST: 0, PENDING: 0, VOID: 0,
                                                            RESOLVED: 0})  # fmt: skip
    primary: ScoreSummary | None = None
    sensitivities: dict[str, ScoreSummary] = field(default_factory=dict)


@dataclass(frozen=True)
class ComparisonResult:
    comparison: Comparison
    result: BootstrapResult
    holm_significant: bool | None = None  # primary family only; meaningful only when confirmatory claims are allowed


@dataclass(frozen=True)
class ModeScores:
    mode: str
    first_day: date | None
    last_day: date | None
    scores: dict[tuple[str, str], QuestionScores]  # (forecaster, question) -> scores
    q5_flag_rate: float | None  # share of the period's question-5 forecast days whose IV30 was flagged
    primary: tuple[ComparisonResult, ...]
    secondary: tuple[ComparisonResult, ...]


class ForecastScorer:
    """`resolvers`: input mode -> its outcome resolver (history scores question 5 against the panel's close IV30, live
    against the forecast's own 15:00 pack IV30; response 69, item 7)."""

    def __init__(self, resolvers: Mapping[str, OutcomeResolver]):
        self.resolvers = resolvers
        self._resolved: dict[tuple[str, str, date], Resolution] = {}

    def resolution(self, mode: str, question: str, day: date) -> Resolution:
        key = (mode, question, day)
        if key not in self._resolved:
            self._resolved[key] = self.resolvers[mode].resolve(question, day)
        return self._resolved[key]

    def score(self, forecasts: Iterable[ScoredForecast]) -> tuple[ModeScores, ...]:
        by_mode: dict[str, list[ScoredForecast]] = defaultdict(list)
        for f in forecasts:
            by_mode[f.mode].append(f)
        return tuple(self._mode(mode, items) for mode, items in sorted(by_mode.items()))

    def _mode(self, mode: str, forecasts: list[ScoredForecast]) -> ModeScores:
        forecasts = sorted(forecasts, key=lambda f: (f.day, f.book, f.question))
        scores = {key: self._question_scores(items) for key, items in _grouped(forecasts).items()}
        q5_days = {f.day: f.iv30_status for f in forecasts if f.question == FORECAST_Q5_RV_BELOW_IV}
        flag_rate = sum(s == FLAGGED for s in q5_days.values()) / len(q5_days) if q5_days else None
        primary = self._comparisons(mode, forecasts, primary_family())
        significant = holm_significant([c.result.p_value for c in primary])
        primary = tuple(ComparisonResult(c.comparison, c.result, s) for c, s in zip(primary, significant, strict=True))
        days = [f.day for f in forecasts]
        return ModeScores(mode, min(days, default=None), max(days, default=None), scores, flag_rate, primary,
                          self._comparisons(mode, forecasts, secondary_comparisons()))  # fmt: skip

    def _question_scores(self, items: Sequence[ScoredForecast]) -> QuestionScores:
        out = QuestionScores()
        pairs: list[tuple[float, bool]] = []
        sensitivity: dict[str, list[tuple[float, bool]]] = defaultdict(list)
        for f in items:
            out.counts["forecasts"] += 1
            if f.probability is None:
                out.counts[NO_FORECAST] += 1
                continue
            res = self.resolution(f.mode, f.question, f.day)
            out.counts[res.status] += 1
            if res.status == RESOLVED:
                pairs.append((f.probability, res.outcome))
                if f.book == BASELINE_RISK_NEUTRAL and f.question in (FORECAST_Q1_UP_20D, FORECAST_Q2_MOVE_3PCT_20D):
                    sensitivity[f"iv30_{'flagged' if f.iv30_status == FLAGGED else 'unflagged'}"].append(
                        (f.probability, res.outcome)
                    )
            elif res.flagged_outcome is not None:
                sensitivity["q5_flagged_iv30"].append((f.probability, res.flagged_outcome))
        out.primary = summarise(pairs)
        out.sensitivities = {name: summarise(values) for name, values in sorted(sensitivity.items())}
        return out

    def _comparisons(self, mode: str, forecasts: list[ScoredForecast], family: Sequence[Comparison]) -> tuple:
        probability = {(f.book, f.question, f.day): f.probability for f in forecasts if f.probability is not None}
        days = sorted({f.day for f in forecasts})
        results = []
        for c in family:
            differences = []
            for day in days:  # date order
                a, b = probability.get((c.first, c.question, day)), probability.get((c.second, c.question, day))
                if a is None or b is None:
                    continue
                res = self.resolution(mode, c.question, day)
                if res.status == RESOLVED:
                    differences.append(brier(a, res.outcome) - brier(b, res.outcome))
            results.append(ComparisonResult(c, compare(differences, c.k)))
        return tuple(results)


def _grouped(forecasts: Iterable[ScoredForecast]) -> dict[tuple[str, str], list[ScoredForecast]]:
    groups: dict[tuple[str, str], list[ScoredForecast]] = defaultdict(list)
    for f in forecasts:
        groups[(f.book, f.question)].append(f)
    return dict(sorted(groups.items()))
