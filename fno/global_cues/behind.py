"""A cue or index whose newest value is older than the session it should hold at the 09:15 open (judge 351 addendum 2,
story A17e): alerted once per episode, so a publisher that slips (as Nasdaq's 03:41 copies did, response 298) is seen
the first morning.

Only names with a real session calendar are judged: a `behind` reading on a Monday-to-Friday calendar is as often a
local holiday as a late publisher, so the world indexes, the US 10-year (bond holidays) and FBIL (a week late by
design) are not. The open episodes are a committed list of names (A20b's `OpenProblems`): names only, never a date or a
value (private cues). A name that turns `behind` prints one `BEHIND` line and fails the run (the workflow's one alert
names it); one still behind prints a quiet reminder; one that caught up prints one line and leaves the list.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from ..circulars.episodes import OpenProblems
from .reading import BEHIND, CueReading

BEHIND_LINE = "{name}: BEHIND, its newest value is older than the session expected by 09:15 IST"
STILL_LINE = "still behind (alerted before): {names}"
CAUGHT_UP_LINE = "{name}: caught up"


class BehindCheck:
    def __init__(self, read: Callable[[str, date], CueReading], names: tuple[str, ...], episodes: OpenProblems):
        """`read(name, day)`: the name's reading at 09:15 IST on that India date, live view."""
        self.read, self.names, self.episodes = read, names, episodes

    def run(self, day: date) -> tuple[list[str], bool]:
        """The lines, and False when a name newly turned behind (the run then fails, so its one alert speaks)."""
        behind = {name for name in self.names if self.read(name, day).status == BEHIND}
        before = self.episodes.read() & set(self.names)
        new, still, cleared = behind - before, behind & before, before - behind
        self.episodes.write(behind)
        lines = [BEHIND_LINE.format(name=name) for name in sorted(new)]
        lines += [STILL_LINE.format(names=", ".join(sorted(still)))] if still else []
        lines += [CAUGHT_UP_LINE.format(name=name) for name in sorted(cleared)]
        return lines, not new
