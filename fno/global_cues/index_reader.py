"""One reading per index from its official cue and its Yahoo cue (story A17e): the official value where it has the date,
Yahoo's otherwise, with the publisher named.

The two cues are read the same way (A17b's `reading_for`, the same cutoff and view); the reading with the newer value
date wins, the official one on a tie. So Nasdaq's own Nasdaq-100 close replaces Yahoo's as soon as Nasdaq publishes it,
and a day Nasdaq is late reads Yahoo's close instead of an older official one (response 298). An index with no official
cue is `verified=False`, shown as "unverified (Yahoo only)".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from .reading import NONE, CueReader, CueReading
from .yahoo_source import UNVERIFIED


@dataclass(frozen=True)
class IndexPair:
    official: str | None  # the official cue, None when the index has none
    yahoo: str


@dataclass(frozen=True)
class IndexReading:
    index: str
    reading: CueReading
    cue: str | None  # the cue the value came from (None: no value)
    verified: bool

    @property
    def label(self) -> str:
        return "" if self.verified else UNVERIFIED


class IndexReader:
    def __init__(self, reader: CueReader, pairs: dict[str, IndexPair]):
        self.reader, self.pairs = reader, pairs

    def read(self, index: str, india_day: date, cutoff: time, live_only: bool) -> IndexReading:
        pair = self.pairs[index]
        cues = [c for c in (pair.official, pair.yahoo) if c is not None and c in self.reader.tables]
        readings = [(cue, self.reader.read(cue, india_day, cutoff, live_only)) for cue in cues]
        dated = [(cue, r) for cue, r in readings if r.row is not None]
        verified = pair.official is not None
        if not dated:
            empty = readings[0][1] if readings else CueReading(None, NONE, None, None)
            return IndexReading(index, empty, None, verified)
        cue, reading = max(dated, key=lambda item: (item[1].row["value_date"], item[0] == pair.official))
        return IndexReading(index, reading, cue, verified)
