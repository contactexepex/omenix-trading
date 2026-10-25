"""Each forecast day's v4 outcome (protocol v4 sections 1-2; story G8), formed from G7's series rules
(`fno/forecast_v4_rules/series.py`, the one place for regular sessions, close-proxy RV_s, the V6 outcomes and A16's
live rv rows; agreed 15 Oct 2026; V7's rule since G7b, 16 Oct) behind `OutcomeSeries`. G8 adds only the horizon sums
(V2, V3) and V1's next-session row. A forecast day whose horizon runs past the data has no entry (unresolved)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import date

from ...constants import (
    V1_RV_1S,
    V2_RV_5S,
    V3_RV_20S,
    V4_RV_BELOW_WEEKLY_IV,
    V5_INSIDE_STRADDLE,
    V6_BIG_MOVE_1S,
    V6_BIG_MOVE_5S,
    V7_VIX_UP_5S,
)
from ...forecast_v4.terms import HORIZON_SESSIONS
from ...forecast_v4_rules.intraday_series import INTRADAY_SERIES, intraday_horizon_sum, question_of
from .inputs import Outcome, V4OutcomeSource

VIX_MISSING = "VIX close missing for {day}{more}: fill it via O6 (no v4 report until then)"


class VixCloseMissing(ValueError):
    """A regular session without its India VIX close: a data fault O6 must fill. Scoring stops and names the day
    rather than void it quietly, which would also change the comparisons' regimes (orchestrator, 16 Oct 2026)."""

    def __init__(self, days: list[date]):
        more = f" (and {len(days) - 1} more)" if len(days) > 1 else ""
        super().__init__(VIX_MISSING.format(day=days[0], more=more))


VOID_PLACEHOLDER = 0.0  # pairs.py reads a None outcome as unresolved before void; a void day's value is never used


class OutcomeSeries(ABC):
    @abstractmethod
    def sessions(self) -> list[tuple[date, float, float]]:
        """(day, official close, closing India VIX) of every A7 regular session, in date order; VixCloseMissing when a
        regular session has no VIX close."""

    @abstractmethod
    def close_proxy_rv(self) -> dict[date, float]:
        """Each regular session's close-proxy RV_s (from the previous regular close)."""

    @abstractmethod
    def big_move_outcomes(self, question: str) -> dict[date, bool]:
        """V6a or V6b's outcome per forecast day, resolved days only."""

    @abstractmethod
    def vix_up_outcomes(self) -> dict[date, bool]:
        """V7's outcome per forecast day (India VIX strictly higher 5 regular sessions later), resolved days only."""

    @abstractmethod
    def intraday_rv(self) -> dict[date, float | None]:
        """A16's live session RV_s per session; None for a void session."""


class OptionOutcomeSource(ABC):
    @abstractmethod
    def outcomes(self, question: str) -> dict[date, bool | None]:
        """V4's or V5's resolved outcome per forecast day; None for a void day; unresolved days are absent."""


class NoOptionOutcomes(OptionOutcomeSource):
    def outcomes(self, question: str) -> dict[date, bool | None]:
        return {}


class SeriesOutcomes(V4OutcomeSource):
    def __init__(self, series: OutcomeSeries, options: OptionOutcomeSource | None = None):
        """`options`: V4's and V5's stored outcomes (G7b completion, part e); none: those questions have none."""
        self.series, self.options = series, options or NoOptionOutcomes()

    def outcomes(self, question: str) -> dict[date, Outcome]:
        sessions = self.series.sessions()
        index = {s[0]: i for i, s in enumerate(sessions)}
        return {
            day: Outcome(value, void, *_first_session(sessions, index[day]))
            for day, (value, void) in self._values(question, sessions).items()
            if index[day] + 1 < len(sessions)
        }

    def _values(self, question: str, sessions) -> dict[date, tuple[object, bool]]:
        days, horizon = [s[0] for s in sessions], HORIZON_SESSIONS[question_of(question)]
        found: dict[date, tuple[object, bool]] = {}
        if question in (V6_BIG_MOVE_1S, V6_BIG_MOVE_5S, V7_VIX_UP_5S):
            outcomes = self._binary(question)
            return {day: (outcomes[day], False) for day in days if day in outcomes}
        if question in (V4_RV_BELOW_WEEKLY_IV, V5_INSIDE_STRADDLE):  # G7b's rules, through their stored records
            options = self.options.outcomes(question)
            return {day: (VOID_PLACEHOLDER if v is None else v, v is None) for day, v in options.items() if day in days}
        rv, intraday = self.series.close_proxy_rv(), self.series.intraday_rv()
        for i, day in enumerate(days[: len(days) - horizon]):
            ahead = days[i + 1 : i + 1 + horizon]
            if question in (V2_RV_5S, V3_RV_20S):
                found[day] = (sum(rv[t] for t in ahead), False)
            elif question == V1_RV_1S and ahead[0] in intraday:
                void = intraday[ahead[0]] is None
                found[day] = (VOID_PLACEHOLDER if void else intraday[ahead[0]], void)
            elif question in INTRADAY_SERIES and (summed := intraday_horizon_sum(intraday, ahead)) is not None:
                found[day] = (VOID_PLACEHOLDER if summed[1] else summed[0], summed[1])
        return found

    def _binary(self, question: str) -> dict[date, bool]:
        """V6a, V6b and V7: G7's shared rules, one place for each (agreed 15 and 16 Oct 2026)."""
        if question == V7_VIX_UP_5S:
            return self.series.vix_up_outcomes()
        return self.series.big_move_outcomes(question)


def _first_session(sessions, i: int) -> tuple[float, float]:
    """The regime inputs: the outcome's first session's closing VIX and its log return."""
    return sessions[i + 1][2], math.log(sessions[i + 1][1] / sessions[i][1])
