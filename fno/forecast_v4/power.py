"""The 60-outcome power report (PROTOCOL_v4.md section 7). It only reports a date: it never changes a threshold, the
family, a baseline, a block length or a look's rate.

After 60 scored outcomes of a member, r = SD(d) / (minimum effect in loss units), where the effect in loss units is the
margin times the baseline's mean loss on the gate set. Independent outcomes needed at a look's first Holm step:
n = ((z(1 - rate / m) + z(power)) x r)^2, rounded up. Independent outcomes a year: 252 / horizon; the scored outcomes
so far count as n_scored / horizon independent ones (overlapping windows are not independent).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

from .terms import (
    FAMILY_SIZE,
    HORIZON_SESSIONS,
    LOOK_ERROR_RATE,
    LOOK_SETTLE_DATE,
    POWER,
    POWER_REPORT_AT,
    SESSIONS_A_YEAR,
    USEFUL_TIME_YEARS,
)


@dataclass(frozen=True)
class PowerReport:
    question: str
    n_scored: int
    r: float
    n_required: int
    years_remaining: float  # from the report's date to the projected settle date
    useful: bool  # settles within 2 years of the report; otherwise the card and the owner are told plainly


def required_outcomes(r: float, rate: float, m: int = FAMILY_SIZE, power: float = POWER) -> int:
    z = NormalDist().inv_cdf
    return math.ceil(((z(1 - rate / m) + z(power)) * r) ** 2)


def noise_ratio(differences: Sequence[float], baseline_mean_loss: float, margin: float) -> float:
    return statistics.stdev(differences) / (margin * baseline_mean_loss)


def power_report(question: str, differences: Sequence[float], baseline_mean_loss: float, margin: float) -> PowerReport:
    """Planned at the settle-date look's rate (0.03 / 15); refused before 60 scored outcomes."""
    if len(differences) < POWER_REPORT_AT:
        raise ValueError(f"the power report waits for {POWER_REPORT_AT} scored outcomes, not {len(differences)}")
    r = noise_ratio(differences, baseline_mean_loss, margin)
    n = required_outcomes(r, LOOK_ERROR_RATE[LOOK_SETTLE_DATE])
    horizon = HORIZON_SESSIONS[question]
    years = max(0.0, n - len(differences) / horizon) / (SESSIONS_A_YEAR / horizon)
    return PowerReport(question, len(differences), r, n, years, years <= USEFUL_TIME_YEARS)
