"""The adapter from G7's series rules (`fno/forecast_v4_rules/series.py`, story G7) to G8's `OutcomeSeries`: G8
re-implements none of them (regular-session filter, close-proxy RV_s, the V6 and V7 outcomes, A16's live rows)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ...constants import V4_RV_BELOW_WEEKLY_IV, V7_VIX_UP_5S
from ...forecast_v4.terms import HORIZON_SESSIONS
from ...forecast_v4_rules import series
from ...forecast_v4_rules.option_history import OptionHistory
from .outcomes import OptionOutcomeSource, OutcomeSeries, VixCloseMissing


class G7Series(OutcomeSeries):
    def __init__(self, closes_text: str, a16_rows: Callable[[], list[dict]]):
        """`closes_text`: `warmup_closes.csv`; `a16_rows`: A16's live `rv/` rows (read only when V1 asks)."""
        self.rows, self.a16_rows = series.closes_rows(closes_text), a16_rows
        self.closes = series.regular_closes(self.rows)

    def sessions(self) -> list[tuple[date, float, float]]:
        vix = {v.day: v.value for v in series.vix_closes(self.rows)}
        missing = [c.day for c in self.closes if c.day not in vix]
        if missing:
            raise VixCloseMissing(missing)
        return [(c.day, c.value, vix[c.day]) for c in self.closes]

    def close_proxy_rv(self) -> dict[date, float]:
        return {v.day: v.value for v in series.close_proxy_rv(self.closes)}

    def big_move_outcomes(self, question: str) -> dict[date, bool]:
        return {o.day: o.value for o in series.big_move_outcomes(self.closes, HORIZON_SESSIONS[question])}

    def vix_up_outcomes(self) -> dict[date, bool]:
        vix = series.vix_closes(self.rows)
        return {
            o.day: o.value
            for o in series.vix_up_outcomes(vix, HORIZON_SESSIONS[V7_VIX_UP_5S], [c.day for c in self.closes])
        }

    def intraday_rv(self) -> dict[date, float | None]:
        return {s.day: s.value for s in series.live_intraday_rv(self.a16_rows())}


class StoredOptionOutcomes(OptionOutcomeSource):
    """V4's and V5's outcomes from G7b's stored terms and outcome records (`forecast_v4_rules.option_history`)."""

    def __init__(self, history: OptionHistory):
        self.history = history

    def outcomes(self, question: str) -> dict[date, bool | None]:
        found = self.history.v4() if question == V4_RV_BELOW_WEEKLY_IV else self.history.v5()
        return {day: outcome.value for day, outcome in found.items()}
