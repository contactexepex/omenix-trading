"""Daily close series for features (story B1): sessions up to a day, without muhurat sessions (Diwali's one-hour
evening session; its closes are not normal daily closes, research/data/nifty-panel/README.md). A session the panel left
out stays in the series with no close, so a window that spans it is incomplete instead of silently longer."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import date
from itertools import pairwise

from ..constants import SESSION_MUHURAT
from ..research_data.panel_reader import NiftyPanel, SessionClose

TRADING_DAYS_PER_YEAR = 252


def daily_sessions(panel: NiftyPanel, through: date) -> list[SessionClose]:
    """Sessions up to and including `through`, muhurat sessions left out."""
    return [s for s in panel.sessions_through(through) if s.session != SESSION_MUHURAT]


def realised_vol_points(closes: list[float | None], returns: int) -> float | None:
    """Root mean square of the last `returns` daily log returns, times sqrt(252), not demeaned, in volatility points.
    Needs the last `returns` + 1 closes all valid (present and positive), else `None`."""
    window = closes[-(returns + 1) :]
    if len(window) < returns + 1 or any(c is None or c <= 0 for c in window):
        return None
    logs = [math.log(later / earlier) for earlier, later in pairwise(window)]
    return math.sqrt(sum(r * r for r in logs) / returns * TRADING_DAYS_PER_YEAR) * 100


def last_valid(sessions: list[SessionClose], value: Callable[[SessionClose], float | None], count: int) -> list[float]:
    """The last `count` valid (present and positive) values of the sessions, oldest first; fewer if there are not
    enough."""
    values = [v for v in map(value, sessions) if v is not None and v > 0]
    return values[-count:] if count else []
