"""The instructor's read adapters over recorded inputs (story MS-INS, parts a and c): b's catalogue and snapshot source
for the captures, A6's events file for the scheduled events, and e's frozen cards for each driver's stop. None reads
anything live."""

from collections.abc import Iterable, Sequence
from datetime import date, datetime

from ...models import now_ist
from ...research_data.events import Event, in_window
from ..constants import RoadCode
from ..contracts.decisions import DriverCard
from ..contracts.roads import RoadCatalogue
from ..contracts.snapshot import SlotSnapshot, SnapshotSource, SnapshotUnavailable
from ..drivers.exits import LOSS_MULTIPLE


class RecordedSnapshotArchive:
    def __init__(self, catalogue: RoadCatalogue, source: SnapshotSource):
        self.catalogue, self.source = catalogue, source

    def snapshot(self, road: RoadCode, session: date) -> SlotSnapshot | None:
        day = next((d for d in self.catalogue.day(session) if d.road.code == road), None)
        if day is None or not day.status.open:
            return None
        try:
            return self.source.for_road(day)
        except SnapshotUnavailable:
            return None


class RecordedEventCalendar:
    def __init__(self, events: Sequence[Event]):
        self.events = list(events)

    def known_between(self, decided_on: date, after: date, through: date) -> tuple[date, ...]:
        return tuple(sorted({e.day for e in in_window(self.events, decided_on, after, through)}))


class IstClock:
    """The real clock, in IST: the reader's "today", up to which corrections are read."""

    def now(self) -> datetime:
        return now_ist()


class CardStops:
    """The stop of each frozen driver card (e's `exit_loss_multiple` parameter), by driver ID."""

    def __init__(self, cards: Iterable[DriverCard]):
        self.multiples = {c.driver_id: c.parameters.get(LOSS_MULTIPLE) for c in cards}

    def loss_multiple(self, driver_id: str) -> float | None:
        value = self.multiples.get(driver_id)
        return None if value is None else float(value)


class NotYetReplayable:
    """The card replay until MS-P1j's fleet can re-run a sealed session: every decision reads "not testable" for cause
    13, counted in every report, never guessed (the real replay is j's recorded-day run, wired here when j lands)."""

    def replay(self, record) -> None:
        return None
