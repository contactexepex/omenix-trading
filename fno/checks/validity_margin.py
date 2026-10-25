"""Margin room as C4 recomputes it (story C4, judge 83), on A14's three-part margins file. Each row holds, per lot, a
structure and width's SPAN scan, net option value (NOV) and exposure margin, with source and date.

- Stressed margin per lot: max(0, k x scan - NOV) + min(0, NOV) + k x exposure (story C2c), with k the owner's
  stressed-margin multiplier (from A14c's factor file, story C2d). A total not above 0 is refused, except 0 for a
  bought-only structure (LC, LP: NSE blocks no margin on a paid-up long option; story STR1).
- Needed: every open trade's stressed margin, plus those of the trades chosen earlier the same day, plus the
  proposal's.
- Available after the entry: the least of
  - cash + the entry's cash flow;
  - marked equity + the entry's cash flow + its marked value;
  - cash + the entry's cash flow + every trade's own liability (the value of each trade worth less than zero);
  then less the premium reserved for pending orders.

A missing, stale or unsourced row, or factor, fails closed. So does a method other than `multiplier`: C4 has no
scenario-lookup arithmetic.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from ..constants import STRESSED_MARGIN_MULTIPLIER, STRUCTURES_BOUGHT_ONLY, STRUCTURES_ONE_SIDE
from .validity_account import Position
from .validity_chain import PricedChain
from .validity_factor import FactorProblem, factor_on
from .validity_proposal import CheckResult
from .validity_settings import MarginSettings
from .validity_stress import marked

COLUMNS = ("structure", "width", "scan_per_lot_rs", "nov_per_lot_rs", "exposure_per_lot_rs", "source", "as_of")
NAME = "margin_room"

CALENDAR_CANNOT_TELL = "margin age for {day} cannot be counted: {reason}"  # the calendar names the year to add


class MarginProblem(ValueError):
    """No usable margin: the trade fails closed."""


class MarginFile:
    def __init__(self, path: Path):
        self.path = path

    def rows(self) -> list[dict[str, str]]:
        if not self.path.is_file():
            raise MarginProblem(f"{self.path.name} is missing")
        with open(self.path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if tuple(reader.fieldnames or ()) != COLUMNS:
                raise MarginProblem(f"{self.path.name}: columns must be A14's {', '.join(COLUMNS)}")
            return list(reader)


def multiplier(settings: MarginSettings, day: date) -> float:
    if settings.method != STRESSED_MARGIN_MULTIPLIER:
        raise MarginProblem(f"stressed margin method {settings.method!r}: C4 checks the multiplier method only")
    try:
        return factor_on(settings.factor_file, day, settings.multiplier_max_age_days)[1]
    except FactorProblem as exc:
        raise MarginProblem(str(exc)) from exc


def margin_row(rows, terms: tuple[str, float, int], day: date, settings: MarginSettings) -> dict:
    """The latest sourced, fresh row for the structure and width on or before `day`."""
    structure, width, _ = terms
    usable = [
        r for r in rows
        if r["structure"] == structure and float(r["width"]) == width and r["source"].strip()
        and date.fromisoformat(r["as_of"]) <= day
    ]  # fmt: skip
    if not usable:
        raise MarginProblem(f"no margin row for {structure} {width:g} on or before {day}")
    row = max(usable, key=lambda r: r["as_of"])
    try:
        fresh = settings.fresh(date.fromisoformat(row["as_of"]), day)
    except ValueError as cannot_tell:  # the calendar's own words name the day and year it cannot answer (story C5c)
        raise MarginProblem(CALENDAR_CANNOT_TELL.format(day=day, reason=cannot_tell)) from cannot_tell
    if not fresh:
        raise MarginProblem(f"margin for {structure} {width:g} is from {row['as_of']}, too old on {day}")
    return row


def span_cap(structure: str, width: float, nov: float, lot_size: int) -> float | None:
    """C4's own cap on the stressed SPAN figure of an STR1 code (story STR1b): 0 for a debit row (the premium is all the
    position can lose), the width less the credit for a credit spread; None (uncapped) for SF, SC and BF."""
    if structure not in STRUCTURES_ONE_SIDE:
        return None
    return max(0.0, width * lot_size + nov) if nov < 0 else 0.0


def stressed_per_lot(rows, terms: tuple[str, float, int], day: date, settings: MarginSettings, lot_size: int) -> float:
    structure, width, _ = terms
    row = margin_row(rows, terms, day, settings)
    scan, nov, exposure = (float(row[k]) for k in ("scan_per_lot_rs", "nov_per_lot_rs", "exposure_per_lot_rs"))
    factor = multiplier(settings, day)
    span, cap = max(0.0, factor * scan - nov), span_cap(structure, width, nov, lot_size)
    capped = span if cap is None else max(max(0.0, scan - nov), min(span, cap))  # never below the broker's own figure
    per_lot = capped + min(0.0, nov) + factor * exposure  # k stresses the exposure too, outside the cap (story C2c)
    if per_lot < 0 or (per_lot == 0 and structure not in STRUCTURES_BOUGHT_ONLY):
        raise MarginProblem(f"margin for {structure} {width:g} on {row['as_of']} is not above 0")
    return per_lot


def _terms(position: Position) -> tuple[str, float, int]:
    if position.terms is None:
        raise MarginProblem(f"open trade {position.trade_id} has no recorded terms (structure, width, lots)")
    return position.terms


def margin_check(
    held: Sequence[Position], proposal: Position, cash: float, premium_reserved: float, chain: PricedChain,
    rows, settings: MarginSettings, day: date, lot_size: int,
) -> CheckResult:  # fmt: skip
    """`held`: the open trades and the trades chosen earlier the same day; `cash` already holds their entries."""
    needed = {
        p.trade_id: stressed_per_lot(rows, _terms(p), day, settings, lot_size) * _terms(p)[2] for p in (*held, proposal)
    }
    values = [marked(p, chain) for p in held]
    own = marked(proposal, chain)
    entry = cash + proposal.cash_flow
    liabilities = sum(min(0.0, v) for v in values) + min(0.0, own)
    after = min(entry, entry + sum(values) + own, entry + liabilities) - premium_reserved
    total = sum(needed.values())
    numbers = {"stressed_margin_rs": {k: round(v, 2) for k, v in needed.items()}, "needed_rs": round(total, 2),
               "available_after_entry_rs": round(after, 2),
               "margin_row": margin_row(rows, _terms(proposal), day, settings)}  # fmt: skip
    reason = f"stressed margin Rs {total:,.2f} against Rs {after:,.2f} available after entry"
    return CheckResult(NAME, total <= after, reason, numbers)
