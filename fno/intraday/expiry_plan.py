"""Which two option chains a snapshot records (story A16): the nearest listed expiry (the weekly) and the nearest
monthly, by A5's point-in-time rule as the 3 pm recorder uses it (A4); when they are the same expiry, the next listed
one is the second chain, so two different chains are always asked for. The near future is the nearest monthly's."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from ..quotes.expiry_listing import ListedExpiries
from ..quotes.monthly_contracts import PointInTimeMonthlies
from ..quotes.recorder import FALLBACK_RULE, POINT_IN_TIME_RULE, UNVERIFIED, VERIFIED, monthly_expiries

UNDERLYING = "NIFTY"
CHAINS = 2


class ExpiryPlanError(RuntimeError):
    """No listed expiry, or no monthly, could be found (the snapshot records the failure; nothing is guessed)."""


@dataclass(frozen=True)
class Expiries:
    nearest: date
    monthly: date
    chains: tuple[date, ...]
    check: dict = field(default_factory=dict)  # how the monthly was chosen (verified, or unverified and why)

    def to_json(self) -> dict:
        return {"nearest": self.nearest.isoformat(), "monthly": self.monthly.isoformat(),
                "chains": [e.isoformat() for e in self.chains], "monthly_check": self.check}  # fmt: skip


class ExpiryPlan:
    def __init__(self, listed: Callable[[], list[date]], fallback: ListedExpiries | None = None,
                 monthlies: PointInTimeMonthlies | None = None):  # fmt: skip
        self.listed, self.fallback, self.monthlies = listed, fallback, monthlies

    def plan(self, day: date) -> Expiries:
        """Groww's list first; NSE's listing is merged in when Groww's list fails, has no monthly, or has no second
        expiry (late December: Groww refuses next year's dates for a week before the last December expiry)."""
        listed, note = self._broker_list(day)
        monthly, check = self._nearest_monthly(listed, day)
        if (monthly is None or len(listed) < CHAINS) and self.fallback is not None:
            listed = sorted(set(listed) | {e for e in self.fallback.listed(UNDERLYING, day)[0] if e >= day})
            monthly, check = self._nearest_monthly(listed, day)
        if monthly is None:
            raise ExpiryPlanError(f"no monthly expiry listed on or after {day}")
        later = [e for e in listed if e != listed[0]]
        second = monthly if monthly != listed[0] else (later[0] if later else None)
        chains = (listed[0],) if second is None else (listed[0], second)
        return Expiries(listed[0], monthly, chains, {**check, **note})

    def _broker_list(self, day: date) -> tuple[list[date], dict]:
        try:
            return sorted(e for e in self.listed() if e >= day), {}
        except Exception as exc:  # recorded in the plan; NSE's listing stands in
            return [], {"broker_list": f"failed: {type(exc).__name__}"}

    def _nearest_monthly(self, listed: list[date], day: date) -> tuple[date | None, dict]:
        if not listed:
            return None, {}
        if self.monthlies is None:
            return _first(monthly_expiries(listed, day)), _unverified("no NSE history wired")
        try:
            monthly, _ = self.monthlies.monthlies(UNDERLYING, listed, day)
        except Exception as exc:  # recorded, never hidden: the last-of-month rule stands in, flagged
            return _first(monthly_expiries(listed, day)), _unverified(f"history unreadable: {type(exc).__name__}")
        return _first(sorted(monthly)), {"status": VERIFIED, "rule": POINT_IN_TIME_RULE}


def _unverified(reason: str) -> dict:
    return {"status": UNVERIFIED, "rule": FALLBACK_RULE, "reason": reason}


def _first(dates: list[date]) -> date | None:
    return dates[0] if dates else None
