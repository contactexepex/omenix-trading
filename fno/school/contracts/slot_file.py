"""One dashcam file per (session, slot, kind) (story 3.4; probe 3: one file a slot): gzip of canonical JSON lines,
each `{"record": ..., "type": ...}`, written with a zero gzip time and no file name so equal records give equal bytes
on every run (a rerun is a no-op, never a replay conflict)."""

import gzip
import json

from .codec import canonical_bytes, from_plain
from .records import DecisionRecord, DriftRow, ExitRecord, OutcomeRecord

RECORD_TYPES = {cls.__name__: cls for cls in (DecisionRecord, ExitRecord, OutcomeRecord, DriftRow)}
SlotRecord = DecisionRecord | ExitRecord | OutcomeRecord | DriftRow


def encode_slot_file(records: tuple[SlotRecord, ...]) -> bytes:
    lines = [_line(record) for record in records]
    return gzip.compress(b"".join(line + b"\n" for line in lines), mtime=0)


def decode_slot_file(data: bytes) -> tuple[SlotRecord, ...]:
    rows = (json.loads(line) for line in gzip.decompress(data).splitlines() if line)
    return tuple(from_plain(RECORD_TYPES[row["type"]], row["record"]) for row in rows)


def _line(record: SlotRecord) -> bytes:
    name = type(record).__name__
    if name not in RECORD_TYPES:
        raise TypeError(f"not a dashcam record: {name}")
    return b'{"record":' + canonical_bytes(record) + b',"type":"' + name.encode("ascii") + b'"}'
