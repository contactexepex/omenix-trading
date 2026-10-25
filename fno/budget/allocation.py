"""The month's Claude plan cost split by measured minutes (story F8; S1's decided item `ai_cost_allocation` of 14 Oct
2026, `research/evaluation/PROTOCOL.md`). Each (purpose, book, role) gets cost x its minutes / all minutes, rounded down
to the paisa; the paise left go to the largest share (most minutes; a tie goes to the first in name order), so the
parts sum exactly to the recorded cost. Development's part is "development, not a book cost". The result is
"allocated, not a bill": the cash spent is the plan's fee, shown apart. No recorded cost: every part is unknown
(None), never zero. When sessions are known to be missing, the meter says which way the book shares are off."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

FORMULA = "minutes_share_v1"
ALLOCATED_LABEL = "allocated, not a bill"
DEVELOPMENT_LABEL = "development, not a book cost"
BOOKS_UNDERSTATED = "{n} fired AI book session(s) not captured: book shares understated"
BOOKS_OVERSTATED = "{reason}: book shares overstated"
UNMEASURED = ("unmeasured", "", "no measured usage")  # where the cost goes in a month with no measured minutes

Share = tuple[str, str, str]  # (purpose, book, role_or_bundle)


@dataclass(frozen=True)
class Allocation:
    month: str
    plan_cost_rs: float | None  # None: the owner has not recorded the month's fee
    minutes: dict[Share, Decimal]
    allocated_rs: dict[Share, float | None]

    @property
    def flagged(self) -> str:
        return (
            "" if self.plan_cost_rs is not None else f"{self.month}: no Claude plan cost recorded; allocation unknown"
        )


def minutes_by_share(usage_rows: list[dict]) -> dict[Share, Decimal]:
    """Exact sums of the ledger's two-decimal minutes, so the split's rounding never depends on float error."""
    minutes: dict[Share, Decimal] = defaultdict(Decimal)
    for row in usage_rows:
        minutes[(row["purpose"], row["book"], row["role_or_bundle"])] += Decimal(row["minutes"])
    return dict(sorted(minutes.items()))


def allocate(month: str, plan_cost_rs: float | None, usage_rows: list[dict]) -> Allocation:
    minutes = minutes_by_share(usage_rows)
    if plan_cost_rs is not None and plan_cost_rs < 0:
        raise ValueError(f"{month}: the Claude plan cost is negative (Rs {plan_cost_rs:,.2f}); record a refund apart")
    if plan_cost_rs is None:
        return Allocation(month, None, minutes, dict.fromkeys(minutes))
    total = sum(minutes.values())
    if total <= 0:
        return Allocation(month, plan_cost_rs, minutes, {UNMEASURED: plan_cost_rs})
    return Allocation(month, plan_cost_rs, minutes, _split(round(plan_cost_rs * 100), minutes, total))


def _split(paise: int, minutes: dict[Share, Decimal], total: Decimal) -> dict[Share, float]:
    parts = {share: int(paise * value // total) for share, value in minutes.items()}
    largest = min(minutes, key=lambda share: (-minutes[share], share))  # most minutes; ties: first in name order
    parts[largest] += paise - sum(parts.values())
    return {share: part / 100 for share, part in parts.items()}


def coverage_warnings(book_missing: int, *gaps: str) -> list[str]:
    """Which way the book shares are off when sessions are missing from the minutes."""
    warnings = [BOOKS_UNDERSTATED.format(n=book_missing)] if book_missing else []
    return warnings + [BOOKS_OVERSTATED.format(reason=gap) for gap in gaps if gap]
