"""A4's 3 pm and 15:15 captures in a rehearsal (story REH1b): the day's recorded attempts, republished at their own
recorded times into the rehearsal's quote store, in place of a live capture. Each attempt's quote file, sidecar and the
day's canonical marker are the real record's own bytes, read only once the replay clock has reached the attempt's
`finished_at` (no look-ahead). It answers the same calls as A4's `QuoteSnapshotRecorder`, which it is built from: its
store, dataset, slot, calendar, clock and sleep are the real recorder's."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime

from ..quotes.recorder import NONE_MARKER, RecordResult
from ..storage.raw_store import RawFileStore

META, CSV = ".meta.json", ".csv"
NOT_RECORDED = "rehearsal: no recorded {kind} attempt of {stem} on {day}"


@dataclass(frozen=True)
class Attempt:
    snapshot_id: str
    meta: dict
    meta_bytes: bytes

    @property
    def finished_at(self) -> datetime:
        return datetime.fromisoformat(self.meta["finished_at"])

    @property
    def in_window(self) -> bool:
        return bool(self.meta.get("in_window"))


class RecordedRecorder:
    def __init__(self, live, record: RawFileStore):
        """`live`: the recorder the composition root built (never asked to capture); `record`: the real record."""
        self.live, self.source, self.store = live, record, live.store
        self.dataset, self.stem, self.now, self.sleep = live.dataset, live.slot.stem, live.now, live.sleep
        self.provider, self.slot, self.underlying = live.provider, live.slot, live.underlying
        self.published: set[str] = set()

    def canonical(self, day: date) -> str | None:
        return self.live.canonical(day)

    def is_session(self, day: date) -> bool:
        return self.live.is_session(day)

    def record(self, outside_window: bool = False) -> RecordResult:
        day = self.now().date()
        if not self.is_session(day):
            return RecordResult("not a trading day")
        if self.canonical(day) is not None:
            return RecordResult("already recorded", self.canonical(day))
        result = RecordResult("window closed", reason=NOT_RECORDED.format(kind="in-window", stem=self.stem, day=day))
        while (attempt := self._next(day, in_window=True)) is not None:
            result = self._publish(day, attempt)
            if result.complete and self.canonical(day) is not None:
                return result
        self.close_day(day)
        return result

    def attempt_now(self) -> RecordResult:
        day = self.now().date()
        if not self.is_session(day):
            return RecordResult("not a trading day")
        if self.canonical(day) is not None:
            return RecordResult("already recorded", self.canonical(day))
        attempt = self._next(day, in_window=True)
        if attempt is None:
            return RecordResult("window closed", reason=NOT_RECORDED.format(kind="in-window", stem=self.stem, day=day))
        return self._publish(day, attempt)

    def capture(self) -> RecordResult:
        """The desk's 15:15 capture: the day's recorded out-of-window attempt started nearest after now."""
        day = self.now().date()
        if not self.is_session(day):
            return RecordResult("not a trading day")
        attempt = self._next(day, in_window=False)
        if attempt is None:
            return RecordResult("window closed", reason=NOT_RECORDED.format(kind="execution", stem=self.stem, day=day))
        return self._publish(day, attempt)

    def close_day(self, day: date) -> None:
        if self.canonical(day) is None and self._marker_in_record(day) in (None, NONE_MARKER):
            self.store.put(self._marker(day), NONE_MARKER.encode())

    def _attempts(self, day: date) -> list[Attempt]:
        folder = f"{self.dataset}/{day:%Y}/{day:%m}"
        prefix = f"{self.stem}_{day:%Y%m%d}_"
        names = sorted(n for n in self.source.checksums(folder) if n.startswith(prefix) and n.endswith(META))
        found = []
        for name in names:
            data = self.source.get(f"{folder}/{name}")
            found.append(Attempt(name.removesuffix(META), json.loads(data), data))
        return found

    def _next(self, day: date, in_window: bool) -> Attempt | None:
        return next((a for a in self._attempts(day) if a.in_window == in_window and a.snapshot_id not in self.published
                     and (in_window or a.finished_at >= self.now())), None)  # fmt: skip

    def _publish(self, day: date, attempt: Attempt) -> RecordResult:
        """Waits for the attempt's own finish time on the replay clock, then writes its record's bytes as A4 did."""
        wait = (attempt.finished_at - self.now()).total_seconds()
        if wait > 0:
            self.sleep(wait)
        folder = f"{self.dataset}/{day:%Y}/{day:%m}"
        csv_path = f"{folder}/{attempt.snapshot_id}{CSV}"
        data = self.source.get(csv_path) if attempt.meta.get("raw_file_saved", True) else None
        if data is not None:
            self.store.put(csv_path, data)
        self.store.put(f"{folder}/{attempt.snapshot_id}{META}", attempt.meta_bytes)
        self.published.add(attempt.snapshot_id)
        if attempt.in_window and self._marker_in_record(day) == attempt.snapshot_id:
            self.store.put(self._marker(day), attempt.snapshot_id.encode())
        rows = max(len(data.splitlines()) - 1, 0) if data else 0
        return RecordResult("recorded", attempt.snapshot_id, bool(attempt.meta.get("complete")), rows,
                            raw_file_error="" if data is not None or not attempt.meta.get("raw_file_saved", True)
                            else "rehearsal: the recorded quote file is not in the record")  # fmt: skip

    def _marker(self, day: date) -> str:
        return f"{self.dataset}/{day:%Y}/{day:%m}/{self.stem}_{day:%Y%m%d}.canonical"

    def _marker_in_record(self, day: date) -> str | None:
        data = self.source.get(self._marker(day))
        return data.decode().strip() if data else None
