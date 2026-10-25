"""The drawdown brake as C4 recomputes it (story C4, judge 83), from the closed equity C4 read off the ledger. The
brake holds new trades while closed equity is the brake amount or more below its high. An owner's restart re-arms it
at that day's closed equity, but only if the brake was in force that day: a restart never loosens a brake that had not
fired, so such a row fails closed."""

from __future__ import annotations

from datetime import date

from .validity_account import AccountFacts
from .validity_proposal import CheckResult

NAME = "drawdown_brake"


def _equity_at(series, day: date) -> float:
    return [value for d, value in series if d <= day][-1]


def drawdown_check(account: AccountFacts, brake: float) -> CheckResult:
    series, anchor = account.closed_equity, None
    high = series[0][1]
    for restart in account.restarts:
        high = max([high] + [v for d, v in series if (anchor is None or d > anchor) and d <= restart])
        at_restart = _equity_at(series, restart)
        if high - at_restart < brake:
            return CheckResult(NAME, False, f"owner restart on {restart}, but the brake was not in force that day")
        anchor, high = restart, at_restart
    high = max([high] + [v for d, v in series if anchor is None or d > anchor])
    closed = series[-1][1]
    drawdown = high - closed
    numbers = {"closed_equity_rs": round(closed, 2), "high_rs": round(high, 2), "drawdown_rs": round(drawdown, 2),
               "brake_rs": brake, "restarted_on": anchor.isoformat() if anchor else ""}  # fmt: skip
    ok = drawdown < brake
    reason = f"closed equity Rs {closed:,.2f} is Rs {drawdown:,.2f} below its high Rs {high:,.2f} (brake {brake:,.0f})"
    return CheckResult(NAME, ok, reason, numbers)
