"""Groww's candles in a rehearsal (story REH1b), behind A16b's `IntradayCandleSource`: the answer Groww gave the day
for the same window, read back from the real record (the manifest of the record checkout, the bytes from the real
Drive, checked against the row's SHA-256). As for A4h's read, the answer served is the one fetched near now, else the
latest fetched before now that day (`serving.scheduled_pick`, REH1q), once the replay clock reaches its fetch time. A
window the day never asked for, or asked only later, is not recorded: `CandleCallFailed`, the back-fill's own
failure, so it is recorded and alerted as any failed call."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from ..intraday.candle_source import FIFTEEN_MINUTES, ONE_MINUTE, CandleAnswer, CandleCallFailed, IntradayCandleSource
from .serving import scheduled_pick

MANIFEST = "nifty-{kind}.csv"
NOT_RECORDED = "rehearsal:NOT_RECORDED Groww {kind} {start}..{end} at {at}: the day fetched no such answer by then"
DAMAGED = "rehearsal: the recorded Groww answer {path} is missing from Drive or differs from its manifest row"


class RecordedCandles(IntradayCandleSource):
    def __init__(self, manifests: Path, read: Callable[[str], bytes | None], now: Callable[[], datetime],
                 sleep: Callable[[float], None]):  # fmt: skip
        self.manifests, self.read, self.now, self.sleep = Path(manifests), read, now, sleep

    def candles(self, start: date, end: date) -> CandleAnswer:
        return self._answer(FIFTEEN_MINUTES, start, end)

    def minute_candles(self, day: date) -> CandleAnswer:
        return self._answer(ONE_MINUTE, day, day)

    def _answer(self, kind: str, start: date, end: date) -> CandleAnswer:
        now = self.now()
        row = self._row(kind, start, end, now)
        if row is None:
            raise CandleCallFailed(NOT_RECORDED.format(kind=kind, start=start, end=end, at=now.isoformat()))
        if (wait := (datetime.fromisoformat(row["fetched_at"]) - self.now()).total_seconds()) > 0:
            self.sleep(wait)
        data = self.read(row["path"])
        if data is None or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise CandleCallFailed(DAMAGED.format(path=row["path"]))
        raw = gzip.decompress(data)
        times = datetime.fromisoformat(row["requested_at"]), datetime.fromisoformat(row["fetched_at"])
        return CandleAnswer(kind, start, end, raw, json.loads(raw)["candles"], *times)

    def _row(self, kind: str, start: date, end: date, now: datetime) -> dict | None:
        manifest = self.manifests / MANIFEST.format(kind=kind)
        rows = list(csv.DictReader(io.StringIO(manifest.read_text(encoding="utf-8")))) if manifest.is_file() else []
        same = [(datetime.fromisoformat(r["fetched_at"]), r) for r in rows
                if (r["kind"], r["start"], r["end"]) == (kind, start.isoformat(), end.isoformat())]  # fmt: skip
        picked = scheduled_pick(now, same)
        return picked[1] if picked else None
