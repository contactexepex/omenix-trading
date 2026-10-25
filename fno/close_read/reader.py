"""`closes read` and `closes read --recheck` (story A4h): on a regular session after the gate, read NSE's index list
(up to 3 tries, 60 s apart), and write the raw answer and the day's record (or, at the recheck, the comparison with the
first read) write-once in Drive. Every run then confirms earlier days, after the read, so a confirm failure never
stops it (judge 447 SF1). Exit 0 when recorded, already recorded, on a
closed day or a non-regular session (printed "nothing written:", so O1 records it refused); exit 1 when too early or
not read, which O1's `Alerted` alerts once (the reader never alerts its own failure)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime

from ..constants import SESSION_REGULAR
from ..research_data.calendar import SessionCalendar
from .answer import ListRead, Refused, difference, read_answer
from .comparison import changed, compared
from .confirm import Confirmer
from .constants import (
    ALREADY_READ,
    ALREADY_RECHECKED,
    AT_RECHECK,
    CLOSE_READ_FROM,
    CLOSE_RECHECK_FROM,
    INDICES,
    NOT_A_SESSION,
    NOT_READ,
    NOT_REGULAR,
    RANGE_FIELDS,
    READ,
    READ_LINE,
    RECHECK,
    RECHECK_LINE,
    TOO_EARLY,
    TRIES,
    TRY_GAP_SECONDS,
)
from .records import encode, raw_path, read_document, recheck_document, recheck_path, record_path
from .source import CloseListSource
from .store import ClosesStore

WITHHELD = "{kind} (message withheld)"  # an error's message can carry a URL; the run log is public


class CloseReader:
    def __init__(self, source: CloseListSource, store: ClosesStore, confirmer: Confirmer, calendar: SessionCalendar,
                 now: Callable[[], datetime], sleep: Callable[[float], None],
                 log: Callable[[str], None] = print):  # fmt: skip
        self.source, self.store, self.confirmer, self.calendar = source, store, confirmer, calendar
        self.now, self.sleep, self.log = now, sleep, log

    def run(self, which: str = READ) -> int:
        started = self.now()
        code = self._read_day(started, which)
        self.confirmer.run(started.date(), started)
        return code

    def _read_day(self, started: datetime, which: str) -> int:
        day = started.date()
        if not self.calendar.is_session(day):
            return self._done(NOT_A_SESSION, 0)
        kind = self.calendar.session_kind(day)
        if kind != SESSION_REGULAR:
            return self._done(NOT_REGULAR.format(kind=kind), 0)
        gate = CLOSE_READ_FROM if which == READ else CLOSE_RECHECK_FROM
        if started.time() < gate:
            return self._done(TOO_EARLY.format(gate=gate), 1)
        written = self.store.written()
        first = record_path(day) in written
        if which == READ and first:
            return self._done(ALREADY_READ.format(day=day), 0)
        if which == RECHECK and (recheck_path(day) in written or (first and raw_path(day, READ) not in written)):
            return self._done(ALREADY_RECHECKED.format(day=day), 0)
        got, raw, reason = self._read(day)
        if got is None:
            return self._done(NOT_READ.format(reason=reason), 1)
        read_at = self.now().isoformat()
        raw_file = (raw_path(day, which), self.store.put(raw_path(day, which), raw))
        if which == RECHECK and first:
            return self._recheck(day, read_at, got, raw_file)
        sha = self.store.put(record_path(day), encode(read_document(day, read_at, got, which, raw_file)))
        how = AT_RECHECK if which == RECHECK else ""
        names = ", ".join(n.listed + ("" if n.checked else " (list)") for n in INDICES)
        problems = "".join(f"; {name}: {', '.join(found)}" for name, found in got.problems.items())
        line = READ_LINE.format(day=day, how=how, names=names, problems=problems, stamp=got.stamp,
                                path=record_path(day), sha=sha[:12])  # fmt: skip
        return self._done(line, 0)

    def _read(self, day) -> tuple[ListRead | None, bytes, str]:
        reason = ""
        for attempt in range(TRIES):
            try:
                payload, raw = self.source.answer()
                return read_answer(payload, day), raw, ""
            except Refused as refused:
                reason = str(refused)
            except Exception as error:  # noqa: BLE001 - a failed read is reported, never raised: O1 alerts on exit 1
                reason = WITHHELD.format(kind=type(error).__name__)
            if attempt < TRIES - 1:
                self.sleep(TRY_GAP_SECONDS)
        return None, b"", reason

    def _recheck(self, day, read_at: str, got: ListRead, raw_file: tuple[str, str]) -> int:
        first = json.loads(self.store.get(record_path(day)))["indices"]
        against = {n.listed: difference(first[n.listed]["last"], got.values[n.listed]["last"]) for n in INDICES}
        fields = {n.listed: compared(first[n.listed], got.values[n.listed], RANGE_FIELDS) for n in INDICES}
        document = recheck_document(day, read_at, got, (against, fields), raw_file)
        sha = self.store.put(recheck_path(day), encode(document))
        results = ", ".join(f"{name} {status}{changed(fields[name])}" for name, status in against.items())
        return self._done(RECHECK_LINE.format(day=day, results=results, stamp=got.stamp, path=recheck_path(day),
                                              sha=sha[:12]), 0)  # fmt: skip

    def _done(self, line: str, code: int) -> int:
        self.log(line)
        return code
