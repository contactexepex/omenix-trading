"""The point-forecast loss of protocol v4 (section 3): the QLIKE ranking loss `ln f + RV / f`, primary, never floored.

The textbook QLIKE `RV / f - ln(RV / f) - 1` equals the ranking loss minus `ln RV + 1`, a term free of the forecast,
so the paired difference of two forecasters is the same under both whenever RV > 0. The textbook form is used only to
size the minimum effect (effect.py), on RV > 0 dates where it is defined.
"""

from __future__ import annotations

import math


class LossInputError(ValueError):
    """A forecast that is not strictly positive and finite, or an observed RV that is negative or not finite."""


def _check(forecast: float, realised: float) -> None:
    if not (math.isfinite(forecast) and forecast > 0):
        raise LossInputError(f"a variance forecast must be finite and > 0, not {forecast!r}")
    if not (math.isfinite(realised) and realised >= 0):
        raise LossInputError(f"an observed realised variance must be finite and >= 0, not {realised!r}")


def ranking_qlike(forecast: float, realised: float) -> float:
    """`ln f + RV / f`; defined at RV = 0 (gives ln f). RV is used exactly as observed."""
    _check(forecast, realised)
    return math.log(forecast) + realised / forecast


def textbook_qlike(forecast: float, realised: float) -> float:
    """`RV / f - ln(RV / f) - 1`; undefined at RV = 0, so it is never asked there."""
    _check(forecast, realised)
    if realised == 0:
        raise LossInputError("the textbook QLIKE is undefined at RV = 0; zero-RV dates are left out of the gate")
    ratio = realised / forecast
    return ratio - math.log(ratio) - 1


def brier(probability: float, outcome: bool) -> float:
    """Squared error of a probability in [0, 1]; never clipped (only the log score clips, as G1)."""
    if not 0.0 <= probability <= 1.0:
        raise LossInputError(f"a probability must lie in [0, 1], not {probability!r}")
    return (probability - float(outcome)) ** 2
