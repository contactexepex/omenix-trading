"""The scorecards as plain text (story E6): book scorecards first, shadow tests in their own section (owner,
experiment 2 option a: a shadow result is evidence, never part of a book's record)."""

from __future__ import annotations

from collections.abc import Sequence

from ..constants import SHADOW_PREFIX
from .scorecard import Scorecard

SAMPLE_UNIT = "Rs C1 net per completed position, before tax"
NONE = "n/a"
MEASURED = " (measurement)"  # story R3: a measurement version's title


def _rs(value: float | None) -> str:
    return NONE if value is None else f"Rs {value:,.2f}"


def _days(value: float | None) -> str:
    return NONE if value is None else f"{value:.1f} days"


def _share(value: float | None) -> str:
    return NONE if value is None else f"{value:.0%}"


def card_lines(card: Scorecard) -> list[str]:
    costs, rev = card.costs, card.review
    low_high = f"{_rs(card.expected_range[0])} to {_rs(card.expected_range[1])}" if card.expected_range else NONE
    lines = [
        f"{card.strategy}{MEASURED if card.measurement else ''} in {card.account} ({card.status})",
        f"  closed trades {len(card.trade_lines)}, net {_rs(card.total_net)}; expected range {low_high} ({card.unit})",
        f"  review sample unit: {SAMPLE_UNIT}",
        f"  half-spread paid {_rs(costs.half_spread_per_unit)}/unit over {costs.units_at_quotes} units "
        f"(research pad {_rs(costs.research_pad_per_unit)}); touch unknown on {costs.touch_unknown} fill(s); "
        f"legging costs {_rs(costs.legging_costs_rs)}",
        f"  entries: {costs.attempts} reached the fill step, {costs.opened} opened, {costs.not_filled} not filled "
        f"({_share(costs.not_filled_share)}); {costs.refused} refused by a gate",
        f"  pending exits: {costs.pending_exits}, mean wait {_days(costs.mean_pending_days)}; "
        f"still waiting: {', '.join(costs.still_pending) or 'none'}",
    ]
    for month, values in card.by_month.items():
        lines.append(f"  {month}: trade net {_rs(values['trade_net'])}")
    for year, values in card.tax_by_year.items():
        lines.append(f"  {year}: tax {_rs(values['tax'])} after tax {_rs(values['after_tax'])} ({values['label']})")
    for mark in card.open_marks:
        lines.append(
            f"  open {mark.trade_id} (not counted): cash flow {_rs(mark.cash_flow)}, at marks {_rs(mark.marked_net)}"
        )
    if rev is not None:
        interval = NONE if rev.interval_rs is None else f"{_rs(rev.interval_rs[0])} to {_rs(rev.interval_rs[1])}"
        lines.append(f"  review {rev.on} (rule {rev.terms_status}): {rev.positions} positions, {rev.months} months, "
                     f"mean {_rs(rev.mean_rs)}, interval {interval}")  # fmt: skip
        lines.append(f"  -> {rev.reason}")
    return lines


def report(cards: Sequence[Scorecard], actions: Sequence[str]) -> list[str]:
    books = [c for c in cards if not c.account.startswith(SHADOW_PREFIX)]
    shadows = [c for c in cards if c.account.startswith(SHADOW_PREFIX)]
    lines = [*actions] or ["automatic pauses: none"]
    for title, group in (("Book scorecards", books), ("Shadow tests (evidence only, never a book's record)", shadows)):
        lines.append(f"== {title} ==")
        lines += [line for card in group for line in card_lines(card)] or ["  none"]
    return lines
