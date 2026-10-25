"""The machine-readable trade of a playbook version (story D2 needs it from the file): which structure, which wing
widths to try, how many lots, and which expiry is an opportunity on which day. The text fields beside them
(`strikes_rule`, `width_rule`, `size_rule`) describe the same rule for people."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..constants import EXPIRY_MONTHLY, STRUCTURES_BOUGHT_ONLY
from .fields import Fields
from .vocabulary import STRUCTURE_CODES

STRUCTURE = ("code", "strikes_rule", "width_rule", "widths", "lots", "expiry")
EXPIRY = ("kind", "min_days", "max_days", "exit_days_before_expiry")


@dataclass(frozen=True)
class ExpiryRule:
    """An opportunity is the first trading day on which an expiry of `kind` is `min_days` to `max_days` calendar days
    away (experiment 1's decision day); the time exit is the last trading day at least `exit_days_before_expiry`
    calendar days before the expiry."""

    kind: str
    min_days: int
    max_days: int
    exit_days_before_expiry: int


@dataclass(frozen=True)
class StructureSpec:
    code: str  # SF, SC, BF or a STR1 code: the code fixes the strikes (research_engine/structures.py, one_side.py)
    strikes_rule: str
    width_rule: str
    widths: tuple[float, ...]  # points out of the money, widest first; the desk keeps the widest within the loss cap
    lots: int
    expiry: ExpiryRule


def parse_structure(fields: Fields) -> StructureSpec:
    code = fields.choice("code", STRUCTURE_CODES)
    return StructureSpec(
        code=code,
        strikes_rule=fields.text("strikes_rule"),
        width_rule=fields.text("width_rule"),
        widths=_widths(fields, code),
        lots=fields.whole("lots", 1),
        expiry=_expiry(fields.section("expiry", EXPIRY)),
    )


def _widths(fields: Fields, code: str) -> tuple[float, ...]:
    """Widest first, no repeats, above 0; a bought-only structure (LC, LP) may also take 0 (the ATM strike)."""
    values = fields.raw("widths")
    numbers = isinstance(values, list) and all(
        isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v) for v in values
    )
    bought_only = code in STRUCTURES_BOUGHT_ONLY
    too_small = numbers and values and (min(values) < 0 if bought_only else min(values) <= 0)
    if not numbers or not values or list(values) != sorted(set(values), reverse=True) or too_small:
        least = "0 or more" if bought_only else "positive"
        raise fields.refuse("widths", f"must be {least} point widths, widest first, no repeats")
    return tuple(float(v) + 0.0 for v in values)  # + 0.0 turns -0.0 into 0.0


def _expiry(fields: Fields) -> ExpiryRule:
    rule = ExpiryRule(
        kind=fields.choice("kind", (EXPIRY_MONTHLY,)),
        min_days=fields.whole("min_days", 1),
        max_days=fields.whole("max_days", 1),
        exit_days_before_expiry=fields.whole("exit_days_before_expiry", 0),
    )
    if rule.max_days < rule.min_days:
        raise fields.refuse("max_days", "must not be below min_days")
    if rule.exit_days_before_expiry >= rule.min_days:
        raise fields.refuse("exit_days_before_expiry", "must be below min_days, so entry comes before the exit")
    return rule
