"""One 15-minute snapshot as stored in Drive (story A16): every call's raw answer with our own request and response
times, kept apart from the source's own times (design 4.4's clock contract). Stored gzip-compressed JSON; the same
document always gives the same bytes, so saving it again changes nothing."""

from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from ..models import IST as _IST

FORMAT = "omenix-intraday-snapshot-v1"
DATASET = "{source}/derivatives/intraday-snapshots"
FILE_NAME = "nifty_{day:%Y%m%d}_{mark:%H%M}_{sha256:.16}.json.gz"
MARK_PREFIX = "nifty_{day:%Y%m%d}_{mark:%H%M}_"


def snapshot_folder(source: str, day: date) -> str:
    """The Drive folder of a session's snapshots: `<publisher>/derivatives/intraday-snapshots/<YYYY>/<MM>/<DD>`."""
    return f"{DATASET.format(source=source)}/{day:%Y}/{day:%m}/{day:%d}"


def snapshot_path(source: str, day: date, mark: datetime, data: bytes) -> str:
    """A copy's archive path. The name carries the copy's SHA-256 (first 16 hex digits), so two runs taking one mark
    write two different names and can never make two Drive files of one name (judge 108 addendum 3)."""
    name = FILE_NAME.format(day=day, mark=mark.astimezone(_IST), sha256=hashlib.sha256(data).hexdigest())
    return f"{snapshot_folder(source, day)}/{name}"


def mark_prefix(day: date, mark: datetime) -> str:
    return MARK_PREFIX.format(day=day, mark=mark.astimezone(_IST))


def utc_text(moment: datetime | None) -> str:
    """Every stored time: UTC with its offset (ISO 8601); empty when unknown."""
    return moment.astimezone(UTC).isoformat() if moment else ""


def parse_time(text: str) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def payload_sha256(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class CallRecord:
    """One request to the source: what was asked (`meta`), when, the raw answer, or the failure's class name only
    (an exception's text could carry a credential, so it is never kept)."""

    name: str
    request_sent_at: datetime
    response_received_at: datetime | None
    payload: dict | list | None
    failure: str = ""
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "name": self.name, "request_sent_at": utc_text(self.request_sent_at),
            "response_received_at": utc_text(self.response_received_at), "failure": self.failure,
            "meta": self.meta, "payload": self.payload,
            "payload_sha256": "" if self.payload is None else payload_sha256(self.payload),
        }  # fmt: skip

    @classmethod
    def from_json(cls, data: dict) -> CallRecord:
        return cls(
            data["name"], parse_time(data["request_sent_at"]), parse_time(data["response_received_at"]),
            data["payload"], data["failure"], data["meta"],
        )  # fmt: skip


@dataclass
class SnapshotDocument:
    source: str
    underlying: str
    session: date
    mark: datetime
    index: CallRecord
    index_level: float | None  # parsed from the index call by the source adapter
    index_source_time: datetime | None  # the source's own time for that level, never our clock
    index_basis: str = ""  # which rule gave the level and its time (index_reading: quote or 1-minute candle)
    index_candle: CallRecord | None = None  # the fallback's candle call, when the quote had no time
    future: CallRecord | None = None
    chains: list[CallRecord] = field(default_factory=list)
    quotes: list[CallRecord] = field(default_factory=list)
    expiries: dict = field(default_factory=dict)
    expected_contracts: int = 0
    two_sided_contracts: int = 0
    failures: list[str] = field(default_factory=list)  # every failed step, by name
    notes: list[str] = field(default_factory=list)  # what went wrong before the mark but was retried (no status)
    finished_at: datetime | None = None  # our clock when the document was complete: its first_seen_at

    @property
    def recorded_contracts(self) -> int:
        return sum(1 for q in self.quotes if not q.failure)

    def to_bytes(self) -> bytes:
        body = {
            "format": FORMAT, "source": self.source, "underlying": self.underlying,
            "session": self.session.isoformat(), "mark": utc_text(self.mark),
            "index_level": self.index_level, "index_source_time": utc_text(self.index_source_time),
            "index_basis": self.index_basis, "index": self.index.to_json(),
            "index_candle": self.index_candle.to_json() if self.index_candle else None,
            "future": self.future.to_json() if self.future else None,
            "chains": [c.to_json() for c in self.chains], "quotes": [q.to_json() for q in self.quotes],
            "expiries": self.expiries, "expected_contracts": self.expected_contracts,
            "recorded_contracts": self.recorded_contracts, "two_sided_contracts": self.two_sided_contracts,
            "failures": self.failures, "notes": self.notes, "finished_at": utc_text(self.finished_at),
        }  # fmt: skip
        text = json.dumps(body, sort_keys=True, default=str, separators=(",", ":")).encode()
        return gzip.compress(text, mtime=0)  # no time in the gzip header: equal documents, equal bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> SnapshotDocument:
        body = json.loads(gzip.decompress(data))
        if body.get("format") != FORMAT:
            raise ValueError(f"not an intraday snapshot of format {FORMAT}")
        future, candle = body["future"], body["index_candle"]
        return cls(
            body["source"], body["underlying"], date.fromisoformat(body["session"]), parse_time(body["mark"]),
            CallRecord.from_json(body["index"]), body["index_level"], parse_time(body["index_source_time"]),
            body["index_basis"], CallRecord.from_json(candle) if candle else None,
            CallRecord.from_json(future) if future else None, [CallRecord.from_json(c) for c in body["chains"]],
            [CallRecord.from_json(q) for q in body["quotes"]], body["expiries"], body["expected_contracts"],
            body["two_sided_contracts"], body["failures"], body["notes"], parse_time(body["finished_at"]),
        )  # fmt: skip
