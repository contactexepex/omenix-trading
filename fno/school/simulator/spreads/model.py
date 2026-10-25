"""The learned spread model and its three labelled scenarios (story MS-SIM-b, 7.2; response 327, correction 6)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ..constants import INSUFFICIENT_SPREAD_LINE, MIN_QUOTED_SESSIONS
from .bucket import SpreadBucket


class Scenario(StrEnum):
    MEDIAN = "median"
    P75 = "p75"
    P95 = "p95"


QUANTILES = {Scenario.MEDIAN: 0.5, Scenario.P75: 0.75, Scenario.P95: 0.95}


def percentile(values: list[float], q: float) -> float:
    """Linear interpolation between the sorted values (the usual 'linear' method); needs at least one value."""
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


@dataclass(frozen=True)
class SpreadScenarios:
    bucket: SpreadBucket
    sessions: int
    half_spreads: Mapping[Scenario, float]  # relative: half the bid-ask gap as a share of the mid

    def half_spread(self, scenario: Scenario) -> float:
        return self.half_spreads[scenario]


@dataclass(frozen=True)
class InsufficientSpreadData:
    bucket: SpreadBucket
    sessions: int

    def __str__(self) -> str:
        return f"{INSUFFICIENT_SPREAD_LINE}: {self.sessions} of {MIN_QUOTED_SESSIONS} quoted sessions for {self.bucket}"


class SpreadModel:
    def __init__(self, by_session: Mapping[SpreadBucket, Mapping[date, float]]):
        """`by_session`: for each bucket, one relative half-spread per quoted session (never per quote)."""
        self.by_session = by_session

    def sessions(self, bucket: SpreadBucket) -> int:
        return len(self.by_session.get(bucket, ()))

    def scenarios(self, bucket: SpreadBucket) -> SpreadScenarios | InsufficientSpreadData:
        values = list(self.by_session.get(bucket, {}).values())
        if len(values) < MIN_QUOTED_SESSIONS:
            return InsufficientSpreadData(bucket, len(values))
        return SpreadScenarios(bucket, len(values), {s: percentile(values, q) for s, q in QUANTILES.items()})
