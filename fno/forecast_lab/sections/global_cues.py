"""Overnight cues from A17's tables (story FL1-1d-2), read only, through A17's own reader (agreed with the A17
builder, 22 Oct): never fetched here, never a second writer. A cue is shown only inside its as-of rule:
- the S&P 500, the Nasdaq-100 and the US 10-year: the last US session before the day's 09:15 IST open (A17's
  `current` or `ahead` at `OPEN`); a `behind` or older reading is not shown as current;
- the RBI's USD/INR reference rate: the same reading, at the edition's own time. In the evening that is its run time,
  when the day's own rate is expected; A17 commits it between about 17:50 and 21:30 IST (its runs on 17-21 Oct,
  judge 451), so when it is not in yet the evening shows the morning's reading (the previous session's rate), said so
  in words, never "not out yet" for a rate that exists;
- Brent: no calendar (EIA prints lag days); the latest print at most `BRENT_DAYS` old, shown with its own date.
The S&P 500 and the Nasdaq-100 are private cues (owner a927390): their values go to Slack and the Drive record only,
never to a repository file (owner bcbbc454)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, time

from ..page.cues import AVAILABLE, CONTEXT, Cue, Section, SectionView, missing
from .spread import changes, size

BRENT_DAYS = 10  # a stated limit (story FL1-1d table), not evidence of the right number
USABLE = ("current", "ahead")
BEHIND = "behind"
NOT_SHOWN = "{label}: no reading yet ({why})"
WHY_NOT_SHOWN = {  # A17's reading states in plain words (orchestrator, 23 Oct: readable in 30 seconds)
    "none": "nothing recorded",
    "behind": "the last one is too old to use",
    "stale": "the last one is far too old to use",
}
EARLIER = "{label}: today's value is not out yet; the previous one is shown, with its date"


@dataclass(frozen=True)
class CueSpec:
    cue: str  # A17's table name
    label: str
    unit: str  # "%" for a level's change, "pts" for a yield's
    calendar: bool = True  # False: Brent, judged by its age only


SPECS = (
    CueSpec("sp500", "S&P 500", "%"),
    CueSpec("nasdaq100", "Nasdaq-100", "%"),
    CueSpec("us10y", "US 10-year yield", "pts"),
    CueSpec("usdinr_rbi", "USD/INR (RBI)", "%"),
    CueSpec("brent", "Brent", "%", calendar=False),
)


class GlobalCueSection(Section):
    def __init__(self, reader: Callable, spec: CueSpec, cutoffs: Mapping[str, tuple[time, ...]]):
        """`reader`: makes A17's `CueReader` (once; it needs the Drive settings, so a missing one fails this Section's
        read, never the page); `cutoffs`: each edition's A17 cutoffs in order, the edition's own time first and an
        earlier fallback after it (what was known by then)."""
        self.reader, self.spec, self.cutoffs, self.name = reader, spec, cutoffs, spec.label

    def _shown(self, reading) -> bool:
        if reading.row is None:
            return False
        if self.spec.calendar:
            return reading.status in USABLE
        return reading.status in (*USABLE, BEHIND) and reading.age_days is not None and reading.age_days <= BRENT_DAYS

    def read(self, day: date, edition: str) -> SectionView:
        reader = self.reader()
        readings = [reader.read(self.spec.cue, day, cutoff, live_only=True) for cutoff in self.cutoffs[edition]]
        shown = next((n for n, r in enumerate(readings) if self._shown(r)), None)
        if shown is None:
            why = WHY_NOT_SHOWN.get(readings[0].status, readings[0].status)
            return missing(self.name, edition, NOT_SHOWN.format(label=self.name, why=why))
        reading, why = readings[shown], (EARLIER.format(label=self.name) if shown else "")
        as_of = date.fromisoformat(reading.row["value_date"])
        rows = [r for r in reader.tables[self.spec.cue].rows() if date.fromisoformat(r["value_date"]) <= as_of]
        values = [float(r["value"]) for r in sorted(rows, key=lambda r: r["value_date"])]
        moves = changes(values, percent=self.spec.unit == "%")
        change = round(moves[-1], 3) if moves else None
        cue = Cue(self.name, values[-1], change, self.spec.unit, as_of, CONTEXT, size=size(change, moves[:-1]))
        return SectionView(self.name, AVAILABLE, as_of, (cue,), why)
