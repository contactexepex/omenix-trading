"""The day's v4 release run (story G10 part 2; judge 282.2's condition; G10 completion, criterion 4): first the
catch-up, then today. The catch-up writes a `system_late` record for every scored session from the go-live date to
yesterday that has no release record **in Drive** (the write-once store decides, never the checkout), so a day the
routine never ran is settled and no look stays blocked. Today: the pack from the day's capture once the capture has
ended, `system_late` when it ended without a complete pack or when the release comes after `V4_RELEASE_BY` (14:45:00,
decision D1), so every pack reader has the same pack well before its 14:55 latest fire. A write-once refusal is named
and the run goes on; nothing is ever overwritten."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from ..constants import V4_DAY_SYSTEM_LATE
from ..forecast_scoring.v4.days import missing_label
from ..models import IST
from ..storage.data_store import DataStore
from ..storage.raw_store import RawFileConflict
from .builder import Built, PackBuilder
from .capture import CaptureSource
from .model import Pack
from .paths import release_path
from .release import publish

# Decision D1 (owner, 24 Oct 2026, DESK_DECISIONS): a release record written later makes the day system_late. Kept
# out of the frozen-to-be `fno/forecast_v4/terms.py`, which G7's and M1's method hashes read (a change there would move
# every record's hash)
V4_RELEASE_BY = time(14, 45)
# Decision D3 (owner, 24 Oct 2026, DESK_DECISIONS): a `system_late` today is a failure of the release (the day ends
# "with problems")
SYSTEM_LATE_FAILS = True
NOT_LIVE = "v4 release: not live (config.yaml daily.live_from.v4_pack is not set or is later)"
RELEASED = "v4 release {day}: {label}{detail}"
CAUGHT_UP = "v4 release {day}: system_late (catch-up: no release record in Drive)"
ALREADY = "v4 release {day}: already released"
WAITING = "v4 release {day}: no complete pack yet ({reasons}); not released before {end:%H:%M}"
REFUSED = "v4 release {day}: REFUSED by the write-once store ({error}); nothing overwritten"
RELEASED_LATE = "released late: after {by:%H:%M}"
NOT_ENDED = "capture still running at {by:%H:%M}"
NOTE = "v4 release {day}: {note}; V4 has no expiry today (add NSE's next-year sessions to the session calendar)"
EXCUSED = "v4 release {day}: system_late ({note})"


def never_excused(day: date) -> str | None:
    return None


class ReleaseRun:
    def __init__(self, store: DataStore, in_drive: Callable[[str], bool], capture: CaptureSource,
                 builder: PackBuilder, sessions: Callable[[date, date], list[date]], live_from: date | None,
                 clock: Callable[[], datetime], excused: Callable[[date], str | None] = never_excused):  # fmt: skip
        """`in_drive(path)`: whether the data store's Drive area holds `path`; `sessions(a, b)`: scored sessions in
        [a, b]; `live_from`: the release's own live date (`daily.live_from.v4_pack`), also the first session the
        catch-up settles (D2 revised: a day before it had no pack to release, so it has no label);
        `excused(day)`: a note when today's `system_late` is no failure (a rehearsal of a day with no recorded capture;
        chosen by the composition root only)."""
        self.store, self.in_drive, self.capture, self.builder = store, in_drive, capture, builder
        self.sessions, self.live_from, self.clock, self.excused = sessions, live_from, clock, excused
        self.refused = self.late_today = self.waiting = False
        self.notes: list[str] = []  # today's alerts beside the label (a V4 expiry the capture could not choose)

    @property
    def failed(self) -> bool:
        """A refused write, a release still waiting for its capture, or (D3) a `system_late` today."""
        return self.refused or self.waiting or (SYSTEM_LATE_FAILS and self.late_today)

    def run(self, today: date) -> list[str]:
        if self.live_from is None or today < self.live_from:
            return [NOT_LIVE]
        lines = [self._catch_up(day, today) for day in self.sessions(self.live_from, today - timedelta(days=1))]
        lines = [line for line in lines if line]
        if today in self.sessions(today, today):
            lines.append(self._today(today))
        return lines

    def _catch_up(self, day: date, today: date) -> str:
        """A past session without a record gets `missing_label`'s answer, written once (the readers' same rule)."""
        if self._released(day) or missing_label(day, self.live_from, today) != V4_DAY_SYSTEM_LATE:
            return ""
        return self._publish(day, None)[0] or CAUGHT_UP.format(day=day)

    def _today(self, day: date) -> str:
        if self._released(day):
            return ALREADY.format(day=day)
        built, by = self._built(day), datetime.combine(day, V4_RELEASE_BY, IST)
        if built.pack is None and not self.capture.ended(day):
            if self.clock() <= by:  # the capture may still write its marker: never settle the day early
                self.waiting = True
                return WAITING.format(day=day, reasons="; ".join(built.reasons), end=by)
            built = Built(None, (NOT_ENDED.format(by=by),))
        refused, label = self._publish(day, built.pack, lambda: self.clock() <= by)
        if refused:
            return refused
        if label != V4_DAY_SYSTEM_LATE:
            self.notes = [NOTE.format(day=day, note=note) for note in built.notes]
            return RELEASED.format(day=day, label=label, detail="")
        note = self.excused(day)
        self.late_today = note is None
        reasons = built.reasons if built.pack is None else (RELEASED_LATE.format(by=by),)  # upload ended after `by`
        detail = f" ({'; '.join(reasons)})"
        return (
            EXCUSED.format(day=day, note=note) if note else RELEASED.format(day=day, label="system_late", detail=detail)
        )

    def _built(self, day: date) -> Built:
        """The pack, unless the release comes after `V4_RELEASE_BY`: then the day is `system_late`."""
        built = self.builder.build(day, self.capture.capture(day))
        by = datetime.combine(day, V4_RELEASE_BY, IST)
        if built.pack is not None and self.clock() > by:
            return Built(None, (RELEASED_LATE.format(by=by),))
        return built

    def _publish(self, day: date, pack: Pack | None, in_time: Callable[[], bool] = lambda: True) -> tuple[str, str]:
        """('', the written label), or (the refusal line, '') when the write-once store refused."""
        try:
            return "", publish(self.store, day, pack, in_time).label
        except RawFileConflict as error:
            self.refused = True
            return REFUSED.format(day=day, error=type(error).__name__), ""

    def _released(self, day: date) -> bool:
        return self.in_drive(f"{self.store.area}/{release_path(day)}")
