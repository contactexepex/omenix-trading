"""One day's margin rows from its beginning-of-day SPAN file (story A14): every structure at every research width
(SF, SC, BF; STR1's one- and two-leg codes too, LC and LP also at width 0, the ATM strike).

The legs are B2's own structures on the file's listed strikes and index close (the ATM strike nearest the close),
on the first monthly expiry at least `min_days_to_expiry` calendar days after the day (the near edge of the entry
window), so a row is the margin of what the desk would open that day. A structure and width that cannot be computed
exactly gets no row and a named reason instead.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..constants import MARGIN_SOURCE_NSE_SPAN
from ..research_engine.structures import Structure
from .calculator import MarginFigure, MarginOutsideModel, SpanMarginCalculator
from .span_file import SpanFile


@dataclass(frozen=True)
class MarginRow:
    structure: str
    width: float
    figure: MarginFigure  # per lot: scan, net option value and exposure, stored apart (judge 75)
    source: str
    as_of: date

    def as_csv(self) -> dict[str, str]:
        f = self.figure
        return {"structure": self.structure, "width": f"{self.width:g}", "scan_per_lot_rs": f"{f.span:.2f}",
                "nov_per_lot_rs": f"{f.nov:.2f}", "exposure_per_lot_rs": f"{f.exposure:.2f}", "source": self.source,
                "as_of": self.as_of.isoformat()}  # fmt: skip


@dataclass(frozen=True)
class DayRows:
    rows: list[MarginRow]
    skipped: list[str]  # what got no row, and why


def span_source(filename: str, sha256: str) -> str:
    """The `source` of a computed row: the exact NSE file and its SHA-256 (A9's manifest has the same)."""
    return f"{MARGIN_SOURCE_NSE_SPAN} {filename} sha256={sha256}"


class MarginRowBuilder:
    def __init__(self, structures: Sequence[Structure], widths: Sequence[float], calculator: SpanMarginCalculator,
                 min_days_to_expiry: int, extra_widths: Mapping[str, Sequence[float]] | None = None):  # fmt: skip
        self.structures, self.widths = tuple(structures), tuple(widths)
        self.calculator, self.min_days_to_expiry = calculator, min_days_to_expiry
        self.extra_widths = dict(extra_widths or {})  # structure code -> widths it gets beyond `widths`

    def widths_for(self, structure: Structure) -> tuple[float, ...]:
        return (*self.widths, *self.extra_widths.get(structure.code, ()))

    def expiry_for(self, span: SpanFile, day: date) -> date:
        later = [e for e in span.monthly_expiries if (e - day).days >= self.min_days_to_expiry]
        if not later:
            raise MarginOutsideModel(f"{span.name}: no monthly expiry {self.min_days_to_expiry}+ days after {day}")
        return min(later)

    def rows(self, span: SpanFile, sha256: str, day: date) -> DayRows:
        expiry, source = self.expiry_for(span, day), span_source(span.name, sha256)
        chain = frozenset(span.series.get(expiry, {}))
        found = DayRows([], [])
        for structure in self.structures:
            for width in self.widths_for(structure):
                what = f"{structure.code} width {width:g}"
                legs = structure.legs(chain, span.underlying, width)
                if legs is None:
                    found.skipped.append(f"{what}: a leg is not listed for {expiry}")
                    continue
                try:
                    figure = self.calculator.per_lot(span, expiry, legs, day)
                except MarginOutsideModel as exc:
                    found.skipped.append(f"{what}: {exc}")
                    continue
                found.rows.append(MarginRow(structure.code, width, figure, source, day))
        return found
