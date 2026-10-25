"""G3, the sample plan (FACTORY_RULES section 1): n = (z x SD / expected net)^2, z from the idea's registered one-sided
pass level, the expected net from its G1 row; above 3 years the idea is an `exploratory_shadow` only (section 3)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

from .constants import PLAN_YEARS_LIMIT, Outcome


@dataclass(frozen=True)
class SamplePlan:
    z: float
    n: int
    years: float

    @property
    def outcome(self) -> Outcome:
        return Outcome.EXPLORATORY_SHADOW if self.years > PLAN_YEARS_LIMIT else Outcome.PLANNED


def sample_plan(sd_per_trade: float, expected_net: float, frequency_per_year: float, pass_level: float) -> SamplePlan:
    if expected_net <= 0:
        raise ValueError("a sample plan needs an expected net above zero (G1 passed)")
    z = NormalDist().inv_cdf(1 - pass_level)
    n = math.ceil((z * sd_per_trade / expected_net) ** 2)
    return SamplePlan(z, n, n / frequency_per_year)
