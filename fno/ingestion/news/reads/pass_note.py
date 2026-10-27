"""The read-pass note (NP8): one small write-once Record file per pass that read in material-first order, holding COUNTS
and the versions and SHA-256 of the two private files it used (the company list and the materiality terms), so the
next pass can refuse to go behind them or to find either edited in place (`news/pin.py`).
`news/read-passes/1/<stamp>.json`, with its receipt and its own manifest `read-passes.csv`. No title, link, key,
symbol or term is ever in it. A pass that read newest first, or probed, writes none, so a red or degraded pass never
moves the pin."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime

from fno.ingestion.news.write_once import WriteOnceWriter, Written
from fno.ingestion.storage.raw_store import RawFileStore

FORMAT = 1
FOLDER = "news/read-passes/1"
STAMP = "%Y%m%dT%H%M%SZ"
KEYS = frozenset(
    {"format", "order", "scored", "material", "asked", "materiality_version", "materiality_sha256", "companies_version",
     "companies_sha256"}
)  # fmt: skip


def note_path(moment: datetime) -> str:
    return f"{FOLDER}/{moment.astimezone(UTC).strftime(STAMP)}.json"


def path_id(path: str) -> str:
    """The manifest id of a note: the SHA-256 of its path, like a cluster file."""
    return hashlib.sha256(path.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class PassNote:
    order: str
    scored: int
    material: int
    asked: int
    materiality_version: int
    materiality_sha256: str
    companies_version: int
    companies_sha256: str

    def to_bytes(self) -> bytes:
        document = {"format": FORMAT, **asdict(self)}
        return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def parse_note(data: bytes) -> PassNote:
    """ValueError for anything that is not a note of ours."""
    try:
        document = json.loads(data)
        if not isinstance(document, dict) or set(document) != KEYS or document["format"] != FORMAT:
            raise ValueError("not a pass note")
        document.pop("format")
        return PassNote(**document)
    except (TypeError, UnicodeDecodeError) as broken:
        raise ValueError("not a pass note") from broken


class PassNotes:
    def __init__(self, record: RawFileStore, writer: WriteOnceWriter):
        """`record`: the Record, read only (the earlier notes); `writer`: the only way to write (`read-passes.csv`)."""
        self.record, self.writer = record, writer

    @property
    def skipped_rows(self) -> int:
        return self.writer.skipped_rows

    def check_ready(self) -> None:
        self.writer.check_ready()

    def last(self) -> PassNote | None:
        """The newest earlier note, or None before the first (ValueError when it is damaged or cannot be read)."""
        names = sorted(name for name in self.record.checksums(FOLDER) if name.endswith(".json"))
        if not names:
            return None
        data = self.record.get(f"{FOLDER}/{names[-1]}")
        if data is None:
            raise ValueError("listed but unreadable")
        return parse_note(data)

    def write(self, note: PassNote, moment: datetime) -> Written:
        return self.writer.write(note_path(moment), note.to_bytes(), date(moment.year, moment.month, moment.day))
