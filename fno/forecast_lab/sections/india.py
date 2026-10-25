"""India's own cues (story FL1-1d-2), each inside its as-of rule:
- India VIX: the previous session's official close in the morning, from NSE's archived index-close file (the morning
  routine archives it first). In the evening it is not shown: the day's official VIX comes with NSE's evening file,
  and the index list's own value differed from it on 21 Oct (15.70 against 15.68), so it is never passed off as the
  close.
- The day's flags: an RBI policy decision or the Union Budget (A6's events) and a NIFTY F&O expiry, dated the day.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date

from ...fo_bhavcopy import BadFile, read_index_closes
from ...research_data.nifty_panel import DailyFiles
from ..page.cues import AVAILABLE, CONTEXT, Cue, Section, SectionView, missing
from ..page.reasons import Facts
from .spread import changes, size

VIX_NAME, VIX_ROW = "India VIX", "India VIX"
VIX_EVENING = "India VIX: the official close comes with NSE's evening file; the live list's value is not the close"
VIX_NOT_ARCHIVED = "India VIX: the official close of {day} is not archived yet"
EXPIRY = "NIFTY F&O expiry today"
NO_FLAGS = "Today's flags"


class VixSection(Section):
    name = VIX_NAME

    def __init__(self, files: DailyFiles, previous: Callable[[date], date], history: Callable[[date], Mapping]):
        """`files`: NSE's archived index-close files; `history`: the VIX closes known by a day (the warm-up table)."""
        self.files, self.previous, self.history = files, previous, history

    def _close(self, day: date) -> float | None:
        filename, data = self.files.get(day)
        try:
            return read_index_closes(data, filename).get(VIX_ROW) if data is not None else None
        except BadFile:
            return None

    def read(self, day: date, edition: str) -> SectionView:
        if edition == "evening":
            return missing(self.name, edition, VIX_EVENING)
        last = self.previous(day)
        close = self._close(last)
        if close is None:
            return missing(self.name, edition, VIX_NOT_ARCHIVED.format(day=last))
        known = self.history(day)
        values = [known[d] for d in sorted(d for d in known if d < last)] + [close]
        moves = changes(values, percent=True)
        change = round(moves[-1], 3) if len(values) > 1 else None
        cue = Cue(self.name, close, change, "%", last, CONTEXT, size=size(change, moves[:-1]))
        return SectionView(self.name, AVAILABLE, last, (cue,))


class FlagsSection(Section):
    name = NO_FLAGS

    def __init__(self, facts: Callable[[date], Facts]):
        """`facts`: what is known by a day (the page's `FactsSource`): A6's events and the NIFTY expiries."""
        self.facts = facts

    def read(self, day: date, edition: str) -> SectionView:
        known = self.facts(day)
        flags = [Cue(text, text=text, as_of=day) for d, text in known.events.items() if d == day]
        flags += [Cue(EXPIRY, text=EXPIRY, as_of=day)] if day in known.expiries else []
        return SectionView(self.name, AVAILABLE, day, tuple(flags))
