"""Archives a latest-day report under the session it covers (judge 66, story P8): fetched, checked, its session read
from the copy itself, then saved at `<dataset>/<YYYY>/<MM>/<DD>/` of that session with its manifest row. A copy covering
a session after the run's day is refused (it cannot exist yet for that run: a re-run of an old day after NSE moved on,
a wrong clock or a wrong file). A session already archived keeps its FIRST copy: a later NSE revision of a provisional
day is not kept, which is the price of point in time (what was known when first taken). Unlike `SnapshotTaker`, a run
never finds its folder taken by another session's copy."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from .coverage import Validator
from .raw_source import NseArchiveSource
from .raw_store import RawFileStore
from .snapshot_taker import ALREADY, NOT_SERVED, TAKEN

FROM_THE_FUTURE = "{path}: the copy covers {session}, after the run's day {day}; refused"
STALE = "{path}: stale: the copy covers {session}, before the run's day {day}; refused"
BEYOND_NEXT = "{path}: the copy covers {session}, after the next trading day following {day}; refused"


class LaterSession(ValueError):
    """The copy covers a session after the run's day: refused, nothing written."""


class StaleCopy(ValueError):
    """The copy covers a session before the run's day where only the day's own copy is valid: refused, nothing
    written."""


CoveredSession = Callable[[str, bytes], date]  # (file name, data) -> the session the copy covers


class SessionFiledTaker:
    def __init__(self, store: RawFileStore, source: NseArchiveSource, validate: Validator, covered: CoveredSession):
        self.store, self.source, self.validate, self.covered = store, source, validate, covered

    def take(self, day: date) -> str:
        """One line saying what happened; ValueError when the copy fails its check, LaterSession when it covers a
        session after `day`."""
        data = self.source.fetch(self.source.path_for(day))  # the publisher's URL does not depend on the day
        if data is None:
            return NOT_SERVED.format(path=self.source.path_for(day))
        self.validate(self.source.FILENAME, data)
        session = self.covered(self.source.FILENAME, data)
        path = self.source.path_for(session)
        self._check(session, day, path)
        existing = self.store.get(path)
        if existing is not None:
            self.store.put(path, existing)  # the same bytes: the store keeps them; the archive's manifest gets its row
            return ALREADY.format(path=path)
        self.store.put(path, data)
        return TAKEN.format(path=path, size=len(data))

    def _check(self, session: date, day: date, path: str) -> None:
        if session > day:
            raise LaterSession(FROM_THE_FUTURE.format(path=path, session=session, day=day))


class CurrentSessionTaker(SessionFiledTaker):
    """For a list valid only for the session it names, published the evening before (A20a's ban list): a copy for a
    session from the run day up to `latest(day)` (the next trading day) is taken under that session; one for an earlier
    session means the publisher has not written today's yet (stale), and one further ahead cannot exist yet."""

    def __init__(self, store: RawFileStore, source: NseArchiveSource, validate: Validator, covered: CoveredSession,
                 latest: Callable[[date], date]):  # fmt: skip
        super().__init__(store, source, validate, covered)
        self.latest = latest

    def _check(self, session: date, day: date, path: str) -> None:
        if session < day:
            raise StaleCopy(STALE.format(path=path, session=session, day=day))
        if session > day and session > self.latest(day):  # asked only past today: the calendar may end today
            raise LaterSession(BEYOND_NEXT.format(path=path, session=session, day=day))
