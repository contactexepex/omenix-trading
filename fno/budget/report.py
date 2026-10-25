"""The printed budget meter and stop-rule lines (story BG1). Cash spend and allocated cost are always separate lines;
anything not recorded or not measured says so, never zero."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .allocation import ALLOCATED_LABEL, DEVELOPMENT_LABEL, FORMULA, UNMEASURED, Allocation
from .cap import BASIS_MEASURED, MEASURED_LIMIT, CapReading, shown_pct
from .constants import BUDGET_NO_CAP, ITEM_CLAUDE_PLAN, NO_SEAL_UPPER_BOUND, PURPOSE_DEVELOPMENT, USAGE_PURPOSES
from .items import ItemLine
from .stop_rule_tracker import ZERO_SHADOWS, ReviewDate, stop_test_status

NOT_RECORDED = "not recorded"
NO_CAP_LINE = "  AI cap: none (owner, 24 Oct 2026: unlimited); books and roles {minutes:,.2f} minutes this month"
# Story BG1-w (owner 24 Oct 2026, "Waiting minutes - Option A"): the AI books' seal-to-reveal wait, shown apart
WAIT_LINE = "  AI books' reveal wait (not capped): {minutes:,.2f} minutes over {runs} run(s)"
NO_WAIT = "  AI books' reveal wait (not capped): none recorded"
UPPER_BOUNDS = "    {runs} run(s) never sealed, counted start to end (no_seal_upper_bound, an upper bound)"


@dataclass(frozen=True)
class MonthMeter:
    month: str
    items: list[ItemLine]
    allocation: Allocation
    cap: CapReading
    usage_rows: list[dict]
    missing_captures: list[tuple[str, str, str, str]]  # (day, book, session link, run)
    needs_owner_yes: list[str]
    unknown_items: list[str]
    allocation_warnings: list[str]
    development_gap: str  # empty when every development session is captured
    routine_gap: str  # empty when every expected data-routine run is captured
    plan_cash: str  # the plan's cash line: a recorded payment, the decided monthly fee, or "not recorded"


def meter_lines(meter: MonthMeter) -> list[str]:
    lines = [f"Omenix F&O budget meter {meter.month} (design v2 section 8.1)"]
    for item in meter.items:
        cash = NOT_RECORDED if item.cash_rs is None else f"Rs {item.cash_rs:,.2f}"
        cash = meter.plan_cash if item.item == ITEM_CLAUDE_PLAN else cash
        lines.append(f"  {item.item}: cash spend {cash}; cap: {item.cap}")
        if item.item == ITEM_CLAUDE_PLAN:
            lines += _allocation_lines(meter.allocation)
            lines += [f"    WARNING: {w}" for w in meter.allocation_warnings if not meter.allocation.flagged]
    lines += [f"  unknown item (not in 8.1): {name}" for name in meter.unknown_items]
    lines += _usage_lines(meter.usage_rows) + _wait_lines(meter.usage_rows) + _cap_lines(meter)
    lines += [f"  NEEDS OWNER: {line}" for line in meter.needs_owner_yes]
    return lines


def _allocation_lines(allocation: Allocation) -> list[str]:
    if allocation.flagged:
        return [f"    {allocation.flagged}"]
    lines = [f"    {ALLOCATED_LABEL} ({FORMULA}):"]
    for (purpose, book, role), rupees in allocation.allocated_rs.items():
        label = f"{role} ({DEVELOPMENT_LABEL})" if purpose == PURPOSE_DEVELOPMENT else f"{purpose} {book or role}"
        if (purpose, book, role) == UNMEASURED:
            label = "not allocated yet (no measured usage this month)"
        lines.append(f"      {label}: Rs {rupees:,.2f}")
    return lines


def _usage_lines(rows: list[dict]) -> list[str]:
    lines = []
    for purpose in USAGE_PURPOSES:
        mine = [r for r in rows if r["purpose"] == purpose]
        if not mine:
            lines.append(f"  measured {purpose}: no rows recorded (unknown, not zero)")
            continue
        minutes = sum(float(r["minutes"]) for r in mine)
        known = all(r["output_tokens"] != "" for r in mine)
        tokens = sum(int(r["output_tokens"]) for r in mine) if known else None
        out = "not available" if tokens is None else f"{tokens:,}"
        sessions = len({r["session_id"] for r in mine})
        lines.append(f"  measured {purpose}: {minutes:,.2f} minutes, {sessions} session(s), output tokens {out}")
    return lines


def _wait_lines(rows: list[dict]) -> list[str]:
    waits = [float(r["wait_minutes"]) for r in rows if r["wait_minutes"] != ""]
    lines = [WAIT_LINE.format(minutes=sum(waits), runs=len(waits)) if waits else NO_WAIT]
    bounds = sum(1 for r in rows if NO_SEAL_UPPER_BOUND in r["source"])  # the rule's name, whatever the wording
    return lines + ([UPPER_BOUNDS.format(runs=bounds)] if bounds else [])


def _cap_lines(meter: MonthMeter) -> list[str]:
    cap = meter.cap
    if cap.level == BUDGET_NO_CAP:  # BG1-u: no cap, so no %, level, basis or coverage lines
        return [NO_CAP_LINE.format(minutes=cap.books_and_roles_minutes)]
    pct = "unknown" if cap.pct_of_cap is None else f"{shown_pct(cap.pct_of_cap):.1f}%"
    lines = [f"  AI cap: books and roles {cap.books_and_roles_minutes:,.2f} of {cap.cap_minutes:,.2f} minutes = {pct}; "
             f"level {cap.level}", f"    basis: {cap.basis}"]  # fmt: skip
    if cap.basis == BASIS_MEASURED:
        lines.append(f"    {MEASURED_LIMIT}")
    if cap.note:
        lines.append(f"    {cap.note}")
    lines.append(f"    {meter.development_gap or 'development capture: complete'}")
    lines.append(f"    {meter.routine_gap or 'data-routine capture: complete'}")
    return lines


def stop_rule_lines(root: Path, review: ReviewDate, today: date) -> list[str]:
    days_left = (review.day - today).days
    lines = ["Omenix F&O stop-rule tracker (design v2 section 8.2)",
             f"  review date: {review.day:%d %b %Y} ({review.basis}); {days_left} days from {today}"]  # fmt: skip
    lines += [f"    {note}" for note in review.notes]
    for test in ("A", "B"):
        status, missing = stop_test_status(root, test)
        lines.append(f"  Test {test}: {status}")
        lines += [f"    missing: {i.what} (story {i.story})" for i in missing]
    lines.append(f"  Test B note: {ZERO_SHADOWS}")
    return lines
