"""Hybrid's envelope (story F5's idea applied to forecasts): per question, Hybrid may answer from `width` below the
lowest available baseline to `width` above the highest, inside [0, 1]. A question with no baseline has no envelope,
so Hybrid answers "no forecast" there. An answer outside is refused for that question, never replaced by the rule
default (that would be imputing).

Protocol v4 (G11 C3, `span`): the span runs from the lower to the higher of the rules slot's value and the primary
baseline's (either alone when the other has none), so Hybrid can always repeat either number (the built "baseline
+-0.10" held the rules' own V6b answer on only 55.5% of 1,908 back-fill days). Probability questions widen it by
`width` absolute, inside [0, 1]; point questions (variances) by `point_width` relative, low x (1 - w) to
high x (1 + w), kept to `SIGNIFICANT` digits (a variance of 1e-4 would lose itself at a fixed 6 decimals)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..constants import BASELINE_BASE_RATE, BASELINE_MODEL, BASELINE_RISK_NEUTRAL
from ..forecast_v4.terms import POINT_QUESTIONS
from .pointer import Rules

BASELINES = (BASELINE_RISK_NEUTRAL, BASELINE_BASE_RATE, BASELINE_MODEL)
ROUNDING = 6  # bounds are printed to the model and compared at this precision, so both sides see the same numbers
SIGNIFICANT = 6  # a variance's bounds: significant digits, rounded outward so the span itself always stays inside


@dataclass(frozen=True)
class Envelope:
    bounds: dict[str, tuple[float, float] | None]  # question -> (low, high), or None: no envelope

    @classmethod
    def from_rules(cls, rules: Rules, width: float) -> Envelope:
        return cls({q: _bounds([by[n] for n in BASELINES if by.get(n) is not None], width) for q, by in rules.items()})

    @classmethod
    def span(cls, values: Mapping[str, Sequence[float]], width: float, point_width: float) -> Envelope:
        """Protocol v4: per question, the values to span (the rules slot's and the primary baseline's, each when it
        has one today)."""
        return cls({q: (_point_bounds(list(v), point_width) if q in POINT_QUESTIONS else _bounds(list(v), width))
                    for q, v in values.items()})  # fmt: skip

    @classmethod
    def from_json(cls, bounds: dict) -> Envelope:
        """The envelope `as_json` wrote (an input's own statement of it)."""
        return cls({q: (tuple(b) if b else None) for q, b in bounds.items()})

    def problem(self, question: str, value: float | None) -> str:
        """Why the answer breaks the envelope, or '' when it is inside (a "no forecast" always is)."""
        if value is None:
            return ""
        allowed = self.bounds.get(question)
        if allowed is None:
            return "no envelope (no baseline today): only null is allowed"
        low, high = allowed
        return "" if low <= value <= high else f"outside the envelope [{low}, {high}]"

    def as_json(self) -> dict[str, list[float] | None]:
        return {q: (list(b) if b else None) for q, b in sorted(self.bounds.items())}


def _bounds(values: list[float], width: float) -> tuple[float, float] | None:
    """From `width` below the lowest value to `width` above the highest, inside [0, 1]; None without a value."""
    if not values:
        return None
    return round(max(0.0, min(values) - width), ROUNDING), round(min(1.0, max(values) + width), ROUNDING)


def _point_bounds(values: list[float], width: float) -> tuple[float, float] | None:
    """A variance's span widened by `width` relative; None without a value."""
    if not values:
        return None
    return _round(min(values) * (1 - width), math.floor), _round(max(values) * (1 + width), math.ceil)


def _round(value: float, direction) -> float:
    """`value` to `SIGNIFICANT` digits, rounded in `direction` (floor for a low bound, ceil for a high one)."""
    if value == 0:
        return 0.0
    scale = 10 ** (SIGNIFICANT - 1 - math.floor(math.log10(abs(value))))
    return direction(value * scale) / scale
