"""Design v2 section 8.1's cost items for one month, from the owner's `accounting/operating_costs.csv` (story C1's
file): the cash spent on each item (None when nothing is recorded: "not recorded", never zero), and the new-cost rule:
any recorded cost other than the two running before 15 Oct 2026, or of an item not in 8.1, and any negative amount,
needs the owner's written yes, shown by citing an existing `docs/DESK_DECISIONS.md` row in the row's `source`."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .constants import (
    BUDGET_ITEMS,
    EXISTING_COST_ITEMS,
    ITEM_AZURE_POSTGRES,
    ITEM_CLAUDE_PLAN,
    ITEM_GITHUB_DRIVE,
    ITEM_GROWW_API,
    ITEM_PAID_DATA,
    ITEM_RECORDER_HOSTING,
)

DECISION_CITATION = "DESK_DECISIONS"
CITATION = re.compile(r"^DESK_DECISIONS (\d{1,2} [A-Z][a-z]{2} \d{4}): (.+)$")  # the row's date and bold title
DECISION_ROW = re.compile(r"^\| ([^|]+?) \| \*\*(.+?)\*\*", re.MULTILINE)
NEEDS_YES = (
    "{month} {item} Rs {amount:,.2f}: a new recurring cost (or a negative amount) needs the owner's written yes: "
    "cite its {cite} row as `DESK_DECISIONS <date>: <bold title>`"
)
CAPS = {  # what 8.1 sets for each item (the AI cap itself is computed in cap.py)
    ITEM_CLAUDE_PLAN: "AI minutes for books and roles; their cap, if any, below",
    ITEM_GITHUB_DRIVE: "no cap needed (free); storage not reported yet: no Drive size source is wired (later)",
    ITEM_AZURE_POSTGRES: "no cap set; owner records the cost",
    ITEM_GROWW_API: "no cap set; owner records any charge",
    ITEM_RECORDER_HOSTING: "a Claude routine (owner, 15 Oct 2026): measured as data_routines minutes, not a cash cost",
    ITEM_PAID_DATA: "none without an idea past the cost wall; owner approves each",
}


@dataclass(frozen=True)
class ItemLine:
    item: str
    cash_rs: float | None  # None: not recorded for the month
    cap: str


def month_items(costs: list[dict], month: str) -> list[ItemLine]:
    rows = [row for row in costs if row["month"] == month]
    return [ItemLine(item, _cash(rows, item), CAPS[item]) for item in BUDGET_ITEMS]


def plan_cost(costs: list[dict], month: str) -> float | None:
    return _cash([row for row in costs if row["month"] == month], ITEM_CLAUDE_PLAN)


def unapproved_costs(costs: list[dict], month: str, decisions: str) -> list[str]:
    """One line per recorded cost of the month that needs the owner's written yes and does not cite an existing
    decision row: its whole `source` must read `DESK_DECISIONS <date>: <bold title>` of a row of the decisions table.
    Whether that row approves this very cost is left to the person reading it (a stated limit)."""
    rows = set(DECISION_ROW.findall(decisions))
    lines = []
    for row in costs:
        amount = float(row["amount_rs"])
        if row["month"] != month or amount == 0 or (row["item"] in EXISTING_COST_ITEMS and amount > 0):
            continue
        if cited_row(row["source"]) not in rows:
            lines.append(NEEDS_YES.format(month=month, item=row["item"], amount=amount, cite=DECISION_CITATION))
    return lines


def cited_row(source: str) -> tuple[str, str] | None:
    """(date, bold title) a cost's source cites, or None when it does not cite one in the required form."""
    match = CITATION.match(source.strip())
    return (match.group(1), match.group(2).strip()) if match else None


def unknown_items(costs: list[dict], month: str) -> list[str]:
    return sorted({row["item"] for row in costs if row["month"] == month and row["item"] not in BUDGET_ITEMS})


def _cash(rows: list[dict], item: str) -> float | None:
    amounts = [float(row["amount_rs"]) for row in rows if row["item"] == item]
    return sum(amounts) if amounts else None
