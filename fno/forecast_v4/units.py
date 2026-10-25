"""V4's units (PROTOCOL_v4.md section 1.4): realised and implied volatility on one session clock.

- Realised: the sum of n session variances `RV_s` (overnight included), annualised on 252 sessions:
  `sigma_RV = sqrt(sum(RV_s) x 252 / n)`.
- Implied: an annualised calendar-clock IV integrates to `IV^2 x calendar days / 365` up to expiry; spread over the
  sessions to expiry and annualised on 252 sessions, `sigma_IV = sqrt(IV^2 x (calendar days / 365) / (sessions / 252))`.
Both are then annualised volatilities per 252 sessions, so `sigma_RV < sigma_IV` compares like with like.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..constants import V4_RV_BELOW_WEEKLY_IV
from .terms import CALENDAR_DAYS_A_YEAR, HORIZON_SESSIONS, SESSIONS_A_YEAR

V4_SESSIONS = HORIZON_SESSIONS[V4_RV_BELOW_WEEKLY_IV]


def realised_vol_annualised(session_variances: Sequence[float]) -> float:
    if not session_variances or any(not (math.isfinite(v) and v >= 0) for v in session_variances):
        raise ValueError("every session variance must be present, finite and >= 0 (a void session voids the day)")
    return math.sqrt(math.fsum(session_variances) * SESSIONS_A_YEAR / len(session_variances))


def implied_vol_session_clock(implied_vol: float, calendar_days: int, sessions: int) -> float:
    """`implied_vol` is annualised on the calendar clock (a decimal, 0.138 for 13.8%)."""
    if not (implied_vol > 0 and calendar_days >= sessions >= V4_SESSIONS):
        raise ValueError("need IV > 0 and an expiry at least 5 sessions out, with calendar days >= sessions")
    return math.sqrt(implied_vol**2 * (calendar_days / CALENDAR_DAYS_A_YEAR) / (sessions / SESSIONS_A_YEAR))


def v4_outcome(session_variances: Sequence[float], implied_vol: float, calendar_days: int, sessions: int) -> bool:
    """True when the next 5 sessions' realised volatility is below the 15:00 implied one, both per 252 sessions."""
    if len(session_variances) != V4_SESSIONS:
        raise ValueError(f"V4 needs exactly {V4_SESSIONS} session variances")
    return realised_vol_annualised(session_variances) < implied_vol_session_clock(implied_vol, calendar_days, sessions)
