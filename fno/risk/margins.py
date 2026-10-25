"""Margins as inputs (story C2): a structure's margin parts per lot, recorded with source and date.

`research/data/margins/margins.csv`: `structure, width, scan_per_lot_rs, nov_per_lot_rs, exposure_per_lot_rs, source,
as_of` (story A14, judge 75): SPAN's scanning risk, the position's net option value (its value at the prices used,
bought legs plus, so a credit structure's is negative) and the exposure margin, stored apart and never one netted
figure. The row used is the latest dated on or before the decision day; a missing row, or one older than the
profile's margin age (`margin_age.py`), fails closed.

The margin C2 counts is `max(0, scan - NOV) + min(0, NOV) + exposure` (judge 75): MarginRoom already moves cash and
marked equity by the entry and takes the lower, so this leaves exactly what a broker that nets the premium into SPAN
leaves free; scan alone counts a debit's premium twice, scan minus NOV a credit's. It must be above 0 (0 or more for a
bought-only structure, LC or LP: story STR1). It is never the broker's live total, whose marked loss available
cash already deducts.

At entry a broker such as Groww credits nothing for the sold premium (it arrives after settlement) and takes the bought
premium at once, so MarginRoom also checks the funds at entry (judge 77 addendum 3): the margin without the premium
credit, `max(0, k x scan - NOV) + k x exposure`, plus the bought premium and charges, against the free cash before
entry.

Stressed margin, one frozen method (`risk.stressed_margin`):
- `multiplier`: the factor k stresses the scanning risk and the exposure, the whole margin as k was measured (owner, 15
  Oct 2026, story C2c); the premium paid or received does not grow (judge 75): `max(0, k x scan - NOV) + min(0, NOV) + k
  x exposure`, with k from A14c's factor file, the latest row before the decision day (`stress_factor.py`, story C2d);
  missing or older than its age fails closed. For SF and SC that is exactly k x what C2 counts; for BF never below it;
  for the STR1 codes the cap below bounds the SPAN part only;
- `scenario_lookup`: a margin per stress scenario from SPAN parameter files (`structure, width, scenario,
  margin_per_lot_rs, source, as_of`); every configured scenario needs a fresh row, and the largest counts.
"""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from ..constants import STRESSED_MARGIN_MULTIPLIER, STRESSED_MARGIN_SCENARIO_LOOKUP, STRESSED_MARGIN_STRESSES
from .capital import stress_cap_per_lot
from .inputs import RiskInputError, TradeTerms
from .margin_age import MarginAge
from .settings import StressedMarginSettings
from .stress_factor import FactorRow, factor_in_force

MARGIN_COLUMNS = ("structure", "width", "scan_per_lot_rs", "nov_per_lot_rs", "exposure_per_lot_rs", "source", "as_of")
SCENARIO_MARGIN_COLUMNS = ("structure", "width", "scenario", "margin_per_lot_rs", "source", "as_of")


def _rows(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.exists():
        raise RiskInputError(f"margin file {path.name} is missing")
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != columns:
            raise RiskInputError(f"{path.name}: columns must be {', '.join(columns)}")
        return list(reader)


def _fresh_row(rows: list[dict[str, str]], what: str, day: date, age: MarginAge) -> dict[str, str]:
    """The latest sourced row dated on or before `day`; refused when there is none or it is too old."""
    dated = [(date.fromisoformat(r["as_of"]), r) for r in rows if r["source"].strip()]
    usable = [(d, r) for d, r in dated if d <= day]
    if not usable:
        raise RiskInputError(f"no margin recorded for {what} on or before {day}")
    as_of, row = max(usable, key=lambda pair: pair[0])
    if not age.fresh(as_of, day):
        raise RiskInputError(f"margin for {what} is from {as_of}, {age.limit()} on {day}")
    return row


def _positive(margin: float, what: str, bought_only: bool) -> float:
    """Above 0, or 0 or more for a bought-only structure (NSE blocks no margin on a paid-up long option, story STR1)."""
    if not (margin >= 0 if bought_only else margin > 0):
        least = "0 or more" if bought_only else "above 0"
        raise RiskInputError(f"margin for {what} must be {least}, not {margin}")
    return margin


@dataclass(frozen=True)
class MarginParts:
    """One lot's margin parts, rupees: SPAN scanning risk, net option value (bought legs plus) and exposure."""

    scan: float
    nov: float
    exposure: float
    what: str
    bought_only: bool = False  # no sold leg (LC, LP): a margin of 0 is right, not a missing row
    span_cap: float | None = None  # STR1 codes: the stressed SPAN figure's cap per lot (capital.py); None: uncapped

    def __post_init__(self):
        if self.scan < 0 or self.exposure < 0:
            raise RiskInputError(f"margin for {self.what}: scan and exposure cannot be negative ({self})")

    def initial(self) -> float:
        """What C2 counts: max(0, scan - NOV) + min(0, NOV) + exposure (judge 75); refused by `_positive`."""
        return self.stressed(1.0)

    def stressed(self, factor: float) -> float:
        """The scanning risk and the exposure times `factor`; the premium paid or received does not grow (C2c)."""
        return _positive(self._span(factor) + min(0.0, self.nov) + factor * self.exposure, self.what, self.bought_only)

    def at_entry(self, factor: float) -> float:
        """The margin blocked at entry when the sold premium is not credited: no `min(0, NOV)` term."""
        return _positive(self._span(factor) + factor * self.exposure, self.what, self.bought_only)

    def _span(self, factor: float) -> float:
        """The SPAN figure at `factor`; with a cap (STR1 codes) the stress extra is capped, never the broker's own
        unstressed figure (C2 is never looser than the broker at entry, judge 77 addendum 3)."""
        span, broker = max(0.0, factor * self.scan - self.nov), max(0.0, self.scan - self.nov)
        return span if self.span_cap is None else max(broker, min(span, self.span_cap))

    @classmethod
    def from_row(cls, row: dict[str, str], what: str, bought_only: bool = False) -> MarginParts:
        names = ("scan_per_lot_rs", "nov_per_lot_rs", "exposure_per_lot_rs")
        return cls(*(float(row[name]) for name in names), what, bought_only)


def _matches(row: dict[str, str], terms: TradeTerms) -> bool:
    return row["structure"] == terms.structure and float(row["width"]) == terms.width


class MarginTable:
    def __init__(self, path: Path, age: MarginAge, lot_size: int):
        self.path, self.age, self.lot_size = path, age, lot_size

    def parts(self, terms: TradeTerms, day: date) -> MarginParts:
        """One lot's margin parts from the latest fresh row for the trade's structure and width."""
        rows = [r for r in _rows(self.path, MARGIN_COLUMNS) if _matches(r, terms)]
        what = f"{terms.structure} width {terms.width:g}"
        parts = MarginParts.from_row(_fresh_row(rows, what, day, self.age), what, terms.bought_only)
        cap = stress_cap_per_lot(terms.structure, terms.width, parts.nov, self.lot_size)
        return replace(parts, span_cap=cap)

    def margin(self, terms: TradeTerms, day: date) -> float:
        """Initial margin of a trade in rupees: the per-lot margin C2 counts x lots."""
        return self.parts(terms, day).initial() * terms.lots


class StressedMargin(ABC):
    method: str

    @abstractmethod
    def margin(self, terms: TradeTerms, day: date) -> float:
        """The trade's margin under stress, in rupees."""

    @abstractmethod
    def margin_at_entry(self, terms: TradeTerms, day: date) -> float:
        """The trade's margin under stress at entry, with no credit for the sold premium, in rupees."""

    @abstractmethod
    def broker_margin(self, terms: TradeTerms, day: date) -> float:
        """What a broker blocks at entry beyond the premium paid, unstressed (factor 1), in rupees (story STR1b)."""

    @abstractmethod
    def record(self, day: date | None = None) -> dict[str, str]:
        """The method in force, for every decision record, so the judge can reproduce it; with a day, what was used
        on it."""


class MultiplierMargin(StressedMargin):
    method = STRESSED_MARGIN_MULTIPLIER

    def __init__(self, table: MarginTable, settings: StressedMarginSettings):
        self.table, self.settings = table, settings

    def margin(self, terms: TradeTerms, day: date) -> float:
        return self.table.parts(terms, day).stressed(self._factor(day)) * terms.lots

    def margin_at_entry(self, terms: TradeTerms, day: date) -> float:
        return self.table.parts(terms, day).at_entry(self._factor(day)) * terms.lots

    def broker_margin(self, terms: TradeTerms, day: date) -> float:
        return self.table.parts(terms, day).at_entry(1.0) * terms.lots

    def _factor(self, day: date) -> float:
        return self._row(day).factor

    def _row(self, day: date) -> FactorRow:
        if self.settings.factor_file is None:
            raise RiskInputError("stressed margin multiplier is not set (risk.stressed_margin.factor_file is required)")
        return factor_in_force(self.settings.factor_file, day, self.settings.max_age_days)

    def record(self, day: date | None = None) -> dict[str, str]:
        """The method and file; with a day, also the factor row in force on it (story C2d)."""
        file = self.settings.factor_file
        method = {"method": self.method, "stresses": STRESSED_MARGIN_STRESSES, "factor_file": file.name if file else ""}
        return method if day is None else method | self._row(day).record()


class ScenarioLookupMargin(StressedMargin):
    method = STRESSED_MARGIN_SCENARIO_LOOKUP

    def __init__(self, settings: StressedMarginSettings, scenarios: Sequence[str], age: MarginAge):
        self.settings, self.scenarios, self.age = settings, tuple(scenarios), age

    def margin(self, terms: TradeTerms, day: date) -> float:
        if self.settings.scenario_file is None:
            raise RiskInputError("stressed margin scenario_lookup has no scenario_file")
        rows = [r for r in _rows(self.settings.scenario_file, SCENARIO_MARGIN_COLUMNS) if _matches(r, terms)]
        per_lot = [self._scenario_margin(rows, terms, name, day) for name in self.scenarios]
        return max(per_lot) * terms.lots

    def margin_at_entry(self, terms: TradeTerms, day: date) -> float:
        """A scenario row is one netted figure with no NOV, so the margin without the premium credit is unknown: fail
        closed rather than be looser than the broker."""
        raise RiskInputError("scenario_lookup rows carry no NOV: the funds at entry cannot be checked")

    def broker_margin(self, terms: TradeTerms, day: date) -> float:
        raise RiskInputError("scenario_lookup rows carry no NOV: the broker margin cannot be split out")

    def _scenario_margin(self, rows: list[dict[str, str]], terms: TradeTerms, name: str, day: date) -> float:
        what = f"{terms.structure} {name}"
        row = _fresh_row([r for r in rows if r["scenario"] == name], what, day, self.age)
        return _positive(float(row["margin_per_lot_rs"]), what, terms.bought_only)

    def record(self, day: date | None = None) -> dict[str, str]:
        file = self.settings.scenario_file
        return {"method": self.method, "scenario_file": file.name if file else ""}
