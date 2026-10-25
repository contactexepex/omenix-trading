"""The AI minutes cap for books and roles (story BG1; owner decisions of 15 Oct 2026: half of the plan's measured
session minutes, alert at 80%, AI roles stop at 100%; "7 A": the measured basis for two months, then a fixed figure).
The plan publishes no minutes allowance, so until `basis_until` the basis is all measured session minutes of the month;
after it, only the owner's own monthly figure. Compared in decimals, so an exact 80% or 100% is never read as just below
it. A level is given only when it is known: on the measured basis it needs every development session captured and every
expected data-routine run captured (missing ones would lower the books' share); missing book sessions can only raise it,
so then `ok` is unknown and `alert` or `stop` is "at least".

Story BG1-u (owner, 24 Oct 2026: "No monthly budget cap for AI. Keep it unlimited."): all of the above holds only under
`budget.cap: share`. Under `none`, the configured value, the reading has the level `no_cap` and no cap at all."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from .constants import (
    BUDGET_ALERT,
    BUDGET_NO_CAP,
    BUDGET_OK,
    BUDGET_STOP,
    BUDGET_UNKNOWN,
    CAP_MODES,
    CAP_SHARE,
    PURPOSE_BOOKS_AND_ROLES,
)

BASIS_MEASURED = "measured: all recorded session minutes of the month (books, roles, development, data routines)"
BASIS_OWNER = "owner's figure: {minutes:,.0f} plan minutes a month (config.yaml budget.plan_minutes_per_month)"
NOTHING_MEASURED = "unknown: no minutes to measure against"
EXPIRED = (
    "unknown: the measured basis ended with {until} (owner's \"7 A\"); the owner's fixed monthly figure is owed "
    "(budget.plan_minutes_per_month)"
)
DEVELOPMENT_GAP = "unknown: {reason}, so the books' measured share is not known"
NOT_CAPTURED = "unknown: {n} fired AI book session(s) not captured, so the true share may be above the alert level"
LOWER_BOUND = "at least this level: {n} fired AI book session(s) not captured would only raise the share"
MEASURED_LIMIT = (
    "limit: the plan's real capacity is not measurable (its rate-limit data gives no minutes), so this basis moves "
    "with development"
)
NO_CAP = "no AI cap (owner, 24 Oct 2026: unlimited)"
BAD_CAP = "budget.cap must be one of {modes}, not {value!r} (owner, 24 Oct 2026: none)"
BAD_SETTINGS = "budget settings must have 0 < books_and_roles_share_pct <= 100 and 0 < alert_pct <= stop_pct"


@dataclass(frozen=True)
class CapSettings:
    share_pct: Decimal  # of the basis, for books and roles
    alert_pct: Decimal
    stop_pct: Decimal
    plan_minutes: Decimal | None  # the owner's own monthly figure, if set
    basis_until: str | None = None  # last month (YYYY-MM) of the measured basis; None: no end set
    capped: bool = True  # BG1-u: False under `budget.cap: none`, the owner's 24 Oct decision

    @classmethod
    def from_config(cls, budget: dict) -> CapSettings:
        mode = budget.get("cap")
        if mode not in CAP_MODES:  # required, never guessed: G11's fire and role_value refuse on a ValueError
            raise ValueError(BAD_CAP.format(modes=", ".join(CAP_MODES), value=mode))
        if mode != CAP_SHARE:  # BG1-u: the share settings are kept in config but neither read nor checked
            return cls(Decimal(0), Decimal(0), Decimal(0), None, capped=False)
        plan, until = budget.get("plan_minutes_per_month"), budget.get("measured_basis_until")
        settings = cls(_dec(budget["books_and_roles_share_pct"]), _dec(budget["alert_pct"]),
                       _dec(budget["stop_pct"]), _dec(plan) if plan is not None else None, until)  # fmt: skip
        if not (0 < settings.share_pct <= 100 and 0 < settings.alert_pct <= settings.stop_pct):
            raise ValueError(BAD_SETTINGS)
        return settings


@dataclass(frozen=True)
class Coverage:
    """What is known to be missing from the month's usage rows."""

    book_missing: int = 0
    development_gap: str = ""  # why development is not fully captured; empty when it is
    routine_gap: str = ""  # why the data routines' runs are not all captured; empty when they are


@dataclass(frozen=True)
class CapReading:
    books_and_roles_minutes: float
    basis_minutes: float
    cap_minutes: float | None  # None: no cap (BG1-u)
    pct_of_cap: float | None  # None: nothing to measure against, or no cap
    level: str
    basis: str
    note: str = ""  # why the level is unknown, or why it is a lower bound


def cap_reading(usage_rows: list[dict], settings: CapSettings, month: str, coverage: Coverage) -> CapReading:
    used = sum((_dec(r["minutes"]) for r in usage_rows if r["purpose"] == PURPOSE_BOOKS_AND_ROLES), Decimal(0))
    owner = settings.plan_minutes is not None
    if owner:
        basis_minutes, basis = _dec(settings.plan_minutes), BASIS_OWNER.format(minutes=_dec(settings.plan_minutes))
    else:
        basis_minutes, basis = sum((_dec(r["minutes"]) for r in usage_rows), Decimal(0)), BASIS_MEASURED
    if not settings.capped:  # BG1-u: minutes still measured and shown; no level, so no gap can make it unknown
        return CapReading(float(used), float(basis_minutes), None, None, BUDGET_NO_CAP, basis, NO_CAP)
    cap = basis_minutes * _dec(settings.share_pct) / 100
    level, note = _gaps(_level(used, cap, settings), owner, settings, month, coverage)
    pct = float(100 * used / cap) if cap > 0 else None
    return CapReading(float(used), float(basis_minutes), float(cap), pct, level, basis, note)


def _gaps(level: str, owner: bool, settings: CapSettings, month: str, coverage: Coverage) -> tuple[str, str]:
    if not owner and settings.basis_until and month > settings.basis_until:
        return BUDGET_UNKNOWN, EXPIRED.format(until=settings.basis_until)
    if level == BUDGET_UNKNOWN:
        missing = f"; {coverage.book_missing} fired AI book session(s) not captured" if coverage.book_missing else ""
        return level, NOTHING_MEASURED + missing
    if not owner and (coverage.development_gap or coverage.routine_gap):
        reasons = "; ".join(r for r in (coverage.development_gap, coverage.routine_gap) if r)
        return BUDGET_UNKNOWN, DEVELOPMENT_GAP.format(reason=reasons)
    if coverage.book_missing and level == BUDGET_OK:
        return BUDGET_UNKNOWN, NOT_CAPTURED.format(n=coverage.book_missing)
    return level, LOWER_BOUND.format(n=coverage.book_missing) if coverage.book_missing else ""


def _level(used: Decimal, cap: Decimal, settings: CapSettings) -> str:
    if cap <= 0:
        return BUDGET_UNKNOWN
    if used * 100 >= cap * _dec(settings.stop_pct):
        return BUDGET_STOP
    return BUDGET_ALERT if used * 100 >= cap * _dec(settings.alert_pct) else BUDGET_OK


def shown_pct(pct: float) -> float:
    """Floored to one decimal, so 99.96% never prints as 100% below the stop level."""
    return math.floor(pct * 10) / 10


def _dec(value) -> Decimal:
    return Decimal(str(value))
