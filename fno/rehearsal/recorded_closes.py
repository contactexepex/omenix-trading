"""A4h's index-list read in a rehearsal (story REH1b), behind its `CloseListSource`: the answer NSE gave on the day,
read back from the real record. The real reader saved its raw answer seconds after asking, so the answer served is the
day's first recorded raw answer saved near now (`serving.scheduled_pick`), once the replay clock reaches its save
time: the 15:40 read gets the first answer, the 16:00 recheck the recheck; a read pushed later than the day's gets the
latest answer of the day saved before it (REH1q). A moment before the day's first answer is not recorded."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime

from ..close_read.source import CloseListSource
from ..storage.receipts import ReceiptFolder
from .serving import scheduled_pick

RAW_SUFFIX = ".raw.json"
NOT_RECORDED = (
    "rehearsal:NOT_RECORDED NSE's index list at {at}: no recorded answer saved before it that day, nor within 10 "
    "minutes after"
)


class RecordedAnswerMissing(RuntimeError):
    """No answer of the day was recorded near this moment, or its raw file is not in the record."""


class RecordedCloseList(CloseListSource):
    def __init__(self, receipts: ReceiptFolder, read: Callable[[str], bytes | None], now: Callable[[], datetime],
                 sleep: Callable[[float], None]):  # fmt: skip
        self.receipts, self.read, self.now, self.sleep = receipts, read, now, sleep

    def answer(self) -> tuple[dict, bytes]:
        now = self.now()
        found = self._served(now, now.date())
        if found is None:
            raise RecordedAnswerMissing(NOT_RECORDED.format(at=now.isoformat()))
        path, saved = found
        if (wait := (saved - self.now()).total_seconds()) > 0:
            self.sleep(wait)
        raw = self.read(path)
        if raw is None:
            raise RecordedAnswerMissing(NOT_RECORDED.format(at=now.isoformat()))
        return json.loads(raw), raw

    def _served(self, now: datetime, day: date) -> tuple[str, datetime] | None:
        prefix = f"data/closes/{day:%Y}/{day:%m}/{day.isoformat()}."
        saved = [(r.path, datetime.fromisoformat(r.written_at)) for r in self.receipts.under(prefix.rsplit("/", 1)[0])
                 if r.path.startswith(prefix) and r.path.endswith(RAW_SUFFIX)]  # fmt: skip
        picked = scheduled_pick(now, ((at, path) for path, at in saved))
        return (picked[1], picked[0]) if picked else None
