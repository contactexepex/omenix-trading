"""The provenance writer (NP11): after a promotion run, puts what the run learned about which feed found which article
into the Record, one file per CLOSED day. It writes only the pairs the day's files do not hold yet: the day file when
there is none, else the next numbered supplement (a late poll). Nothing is rewritten; the file goes through the same
write-once path as every derived file (Drive, receipt, then the `provenance.csv` row)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime

from fno.ingestion.news import codes
from fno.ingestion.news.provenance import file
from fno.ingestion.news.provenance.index import ProvenanceIndex, ProvenanceUnreadable
from fno.ingestion.news.provenance.model import UNKNOWN, Pair, Pairs, day_of, path_of
from fno.ingestion.news.write_once import WriteOnceWriter
from fno.ingestion.storage.raw_store import RawFileConflict
from fno.shared.models import now_utc


class ProvenanceCollector:
    """The pairs one promotion run saw, by IST day of the poll."""

    def __init__(self, scopes: dict[str, str]):
        self.scopes = scopes  # feed id -> scope, UNKNOWN when the list does not label it
        self.days: dict[date, dict[str, set[Pair]]] = defaultdict(lambda: defaultdict(set))

    def add(self, feed: str, moment: datetime, keys: list[str]) -> None:
        pair = (feed, self.scopes.get(feed, UNKNOWN))
        for key in keys:
            self.days[day_of(moment)][key].add(pair)


class ProvenanceWriter:
    def __init__(
        self, index: ProvenanceIndex, writer: WriteOnceWriter, salt: str, today: Callable[[], date] | None = None
    ):
        self.index, self.writer, self.salt = index, writer, salt
        self.today = today or (lambda: day_of(now_utc()))

    def check_ready(self) -> None:
        self.writer.check_ready()

    def flush(self, collected: dict[date, dict[str, set[Pair]]], report) -> int:
        """Files written. The open day is skipped until it is over; a damaged or conflicting day is counted and left."""
        written = 0
        for day in sorted(d for d in collected if d < self.today()):
            try:
                missing = self._missing(day, collected[day])
                if missing:
                    self._write(day, missing)
                    written += 1
            except ProvenanceUnreadable:
                report.reject(codes.PROVENANCE_UNREADABLE)
            except RawFileConflict:
                report.reject(codes.PROVENANCE_CONFLICT)
            except Exception:  # noqa: BLE001 - Drive's own errors may name paths; only the code is kept
                report.reject(codes.PROVENANCE_FAILED)
        return written

    def _missing(self, day: date, seen: dict[str, set[Pair]]) -> Pairs:
        held = self.index.pairs(day)
        wanted = {key: frozenset(pairs - held.get(key, frozenset())) for key, pairs in seen.items()}
        return {key: pairs for key, pairs in wanted.items() if pairs}

    def _write(self, day: date, pairs: Pairs) -> None:
        number = self.index.next_number(day)
        self.writer.write(path_of(day, number), file.to_bytes(day, number, self.salt, pairs), day)
        self.index.forget(day)
