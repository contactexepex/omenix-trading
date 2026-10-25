"""`v7_vix_vs_mean20` (story G7b; V7, reported and descriptive only): the base rate of "VIX higher in 5 sessions"
conditioned on which side of its 20-session mean VIX sat. It is the two-cell rival that `PROTOCOL_v4_calibration.md`
section 3 measured (`tools/v4_vix_null.py`), lagged one session for the 14:30 cutoff: `d`'s own VIX close is not
known then, so the forecast for `d` reads the side at `d-1`, and each past day `t` is filed under its side at `t-1`.
Zero fitted parameters (design 5.7 rule 5)."""

from __future__ import annotations

from datetime import date

from .baselines import MINIMUM, NOT_ELIGIBLE, WINDOW, Value, before
from .series import DayValue, Outcome

MEAN_SESSIONS = 20  # the measured rival's mean: the session itself and the 19 before it
MIN_CELL = 100  # the measured rival's cell minimum; a smaller cell falls back to the window's plain share


class VixSideRate:
    def __init__(self, vix: list[DayValue], outcomes: list[Outcome], sessions: list[date]):
        """`sessions`: the regular sessions in order. A 20-session window with a missing VIX close has no side, so
        a gap never stretches the mean (judge 267)."""
        known = {v.day: v.value for v in vix}
        values = [known.get(d) for d in sessions]
        self.days = list(sessions)
        self.below = [
            self._below(values[i - MEAN_SESSIONS + 1 : i + 1]) if i >= MEAN_SESSIONS - 1 else None
            for i in range(len(values))
        ]
        self.outcomes = sorted(outcomes, key=lambda o: o.resolved_on)
        self.resolved = [o.resolved_on for o in self.outcomes]

    @staticmethod
    def _below(window: list[float | None]) -> bool | None:
        if None in window:
            return None
        return window[-1] < sum(window) / MEAN_SESSIONS

    def side_before(self, d: date) -> bool | None:
        """Whether VIX was below its 20-session mean at the last session before `d` (None before 20 sessions)."""
        i = before(self.days, d) - 1
        return self.below[i] if i >= 0 else None

    def forecast(self, d: date) -> Value:
        """Among the most recent 750 outcomes resolved before `d` (at least 500, as the base rate), the share of 1s
        whose day was on `d`'s side; with fewer than 100 on that side, the window's plain share."""
        end = before(self.resolved, d)
        window = self.outcomes[max(0, end - WINDOW) : end]
        side = self.side_before(d)
        if len(window) < MINIMUM or side is None:
            return Value(NOT_ELIGIBLE)
        cell = [o for o in window if self.side_before(o.day) == side]
        chosen = cell if len(cell) >= MIN_CELL else window
        return Value.of(sum(o.value for o in chosen) / len(chosen), positive=False)
