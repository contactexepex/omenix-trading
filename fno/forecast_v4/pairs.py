"""The two frozen date sets of a v4 comparison (PROTOCOL_v4.md section 4).

- **Scored set** (the primary significance test): every date, in date order, where the outcome resolved, the date is
  not void, and both the forecaster and the primary baseline forecast. Zero-RV dates stay in; a zero difference stays
  in. Missing forecasts, missing baselines, void and unresolved dates are dropped and counted, never imputed.
- **Gate set** (the minimum effect of a point question): the scored dates with RV > 0, where the textbook QLIKE is
  defined. The zero-RV dates it leaves out are counted. For a probability question it is the scored set itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .loss import brier, ranking_qlike, textbook_qlike


@dataclass(frozen=True)
class DatedForecasts:
    day: date
    forecast: float | None  # the registered forecaster's value; None when it did not forecast
    baseline: float | None  # the primary baseline's value; None when not eligible or missing
    outcome: float | bool | None  # RV (point) or the event (probability); None while unresolved
    void: bool = False  # the question's void rule (protocol section 2)


@dataclass(frozen=True)
class PairedSet:
    days: tuple[date, ...]
    differences: tuple[float, ...]  # loss(forecaster) - loss(baseline); negative favours the forecaster
    baseline_losses: tuple[float, ...]  # the gate's denominator terms (textbook QLIKE or Brier of the baseline)


@dataclass(frozen=True)
class Pairing:
    scored: PairedSet
    gate: PairedSet
    missing_forecast: int
    missing_baseline: int  # includes dates the baseline was not eligible
    void: int
    unresolved: int
    zero_rv_left_out_of_gate: int


def pair_point(rows: Sequence[DatedForecasts]) -> Pairing:
    """A point variance question: the ranking loss on the scored set, the textbook loss on the gate set."""
    counts, kept = _filter(rows)
    scored = _paired(kept, ranking_qlike, ranking_qlike)
    positive = [r for r in kept if r.outcome > 0]
    gate = _paired(positive, ranking_qlike, textbook_qlike)
    return Pairing(scored, gate, *counts, zero_rv_left_out_of_gate=len(kept) - len(positive))


def pair_probability(rows: Sequence[DatedForecasts]) -> Pairing:
    """A probability question: Brier on the scored set, which is also the gate set."""
    counts, kept = _filter(rows)
    scored = _paired(kept, brier, brier)
    return Pairing(scored, scored, *counts, zero_rv_left_out_of_gate=0)


def _filter(rows: Sequence[DatedForecasts]) -> tuple[tuple[int, int, int, int], list[DatedForecasts]]:
    missing_forecast = missing_baseline = void = unresolved = 0
    kept = []
    for row in sorted(rows, key=lambda r: r.day):
        if row.outcome is None:
            unresolved += 1
        elif row.void:
            void += 1
        elif row.forecast is None:
            missing_forecast += 1
        elif row.baseline is None:
            missing_baseline += 1
        else:
            kept.append(row)
    if len({r.day for r in rows}) != len(rows):
        raise ValueError("one row per date: a comparison never holds two forecasts for one day")
    return (missing_forecast, missing_baseline, void, unresolved), kept


def _paired(rows: Sequence[DatedForecasts], loss, baseline_loss) -> PairedSet:
    differences = tuple(loss(r.forecast, r.outcome) - loss(r.baseline, r.outcome) for r in rows)
    return PairedSet(tuple(r.day for r in rows), differences, tuple(baseline_loss(r.baseline, r.outcome) for r in rows))
