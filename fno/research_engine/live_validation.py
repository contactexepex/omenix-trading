"""Validation of a live 15:00 feature against its daily-close research version (story B7).

For every recorded day (a canonical A4 snapshot) that the panel also covers, both versions are computed for the same
context and compared: mean and largest absolute difference where both are numbers, and the share of days where the
policy's decision state is the same. Policies have three states per feature (policies.py): a number is above zero,
at most zero, or unknown (None); a flag is true, false or unknown. So a live None against a close value is a
disagreement unless the close value is also None (judge 44). Use rule (frozen per strategy in its playbook, story D1):
a live feature may drive paper decisions only with at least `min_days` compared days, a state agreement of at least
`min_agreement` and a live value on at least `min_available` of the days. Disagreement days and each day's capture
time are listed for the red team.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime

from .features import DecisionContext, Feature, FeatureValue, ResearchData

MIN_DAYS, MIN_AGREEMENT, MIN_AVAILABLE = 20, 0.90, 0.90  # story B7 proposal; the owner may set stricter values
ABOVE_ZERO, NOT_ABOVE_ZERO, TRUE, FALSE, UNKNOWN = "above_zero", "not_above_zero", "true", "false", "unknown"


@dataclass(frozen=True)
class LiveUseRule:
    min_days: int = MIN_DAYS
    min_agreement: float = MIN_AGREEMENT
    min_available: float = MIN_AVAILABLE

    def passes(self, days: int, agreement: float | None, available: float | None) -> bool:
        return days >= self.min_days and agreement >= self.min_agreement and available >= self.min_available


def decision_state(value: FeatureValue) -> str:
    """The state a policy condition sees: Positive / NotPositive for numbers, IsTrue / IsFalse for flags, else
    unknown."""
    if value is None:
        return UNKNOWN
    if isinstance(value, bool):
        return TRUE if value else FALSE
    return ABOVE_ZERO if value > 0 else NOT_ABOVE_ZERO


@dataclass(frozen=True)
class DayComparison:
    day: date
    live: FeatureValue
    close: FeatureValue
    captured_at: datetime | None = None  # when the day's A4 capture finished (a capture after the cutoff gives None)

    @property
    def agrees(self) -> bool:
        return decision_state(self.live) == decision_state(self.close)

    @property
    def difference(self) -> float | None:
        numbers = all(isinstance(v, float) and not isinstance(v, bool) for v in (self.live, self.close))
        return abs(self.live - self.close) if numbers else None


def agreement_numbers(
    comparisons: Sequence[tuple[FeatureValue, FeatureValue]],
) -> tuple[int, float | None, float | None]:
    """(days, state agreement, live availability) of (live, close) value pairs."""
    days = len(comparisons)
    if not days:
        return 0, None, None
    agree = sum(decision_state(live) == decision_state(close) for live, close in comparisons)
    return days, agree / days, sum(live is not None for live, _ in comparisons) / days


@dataclass(frozen=True)
class ValidationReport:
    live_feature: str
    close_feature: str
    comparisons: tuple[DayComparison, ...]
    rule: LiveUseRule

    @property
    def numbers(self) -> tuple[int, float | None, float | None]:
        return agreement_numbers([(c.live, c.close) for c in self.comparisons])

    @property
    def differences(self) -> list[float]:
        return [d for d in (c.difference for c in self.comparisons) if d is not None]

    @property
    def validated(self) -> bool:
        return self.rule.passes(*self.numbers)

    def summary(self) -> dict:
        days, agreement, available = self.numbers
        diffs = self.differences
        return {
            "live_feature": self.live_feature, "close_feature": self.close_feature, "days": days,
            "agreement": agreement, "live_available": available,
            "mean_abs_difference": sum(diffs) / len(diffs) if diffs else None,
            "largest_abs_difference": max(diffs) if diffs else None, "validated": self.validated,
            "rule": asdict(self.rule),
            "disagreement_days": [c.day.isoformat() for c in self.comparisons if not c.agrees],
            "comparisons": [
                {
                    "day": c.day.isoformat(), "live": c.live, "close": c.close, "agrees": c.agrees,
                    "captured_at": c.captured_at.isoformat() if c.captured_at else None,
                }
                for c in self.comparisons
            ],
        }  # fmt: skip


def validate(
    live: Feature,
    close: Feature,
    data: ResearchData,
    days: Sequence[date],
    context_for: Callable[[date], DecisionContext | None],
    rule: LiveUseRule | None = None,
) -> ValidationReport:
    """Compares the two versions on every recorded day the panel covers and that has a context."""
    comparisons = []
    for day in days:
        context, session, snapshot = context_for(day), data.panel.session_on(day), data.snapshots.get(day)
        if snapshot is None or context is None or session is None or session.underlying is None:
            continue
        live_value, close_value = live.value(data, day, context), close.value(data, day, context)
        comparisons.append(DayComparison(day, live_value, close_value, snapshot.finished_at))
    return ValidationReport(live.name, close.name, tuple(comparisons), rule or LiveUseRule())
