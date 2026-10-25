"""One instructor file per (session, kind): gzip of canonical JSON lines, zero gzip time and no file name, as the
dashcam's slot files, so equal records give equal bytes on every run."""

import gzip
import json

from ..contracts.codec import canonical_bytes, from_plain
from .contracts import Attribution, Classification, PairedRow
from .ports import InstructorRecord

RECORD_TYPES = {cls.__name__: cls for cls in (Attribution, Classification, PairedRow)}


def encode_instructor_file(records: tuple[InstructorRecord, ...]) -> bytes:
    return gzip.compress(b"".join(_line(record) + b"\n" for record in records), mtime=0)


def decode_instructor_file(data: bytes) -> tuple[InstructorRecord, ...]:
    rows = (json.loads(line) for line in gzip.decompress(data).splitlines() if line)
    return tuple(from_plain(RECORD_TYPES[row["type"]], row["record"]) for row in rows)


def _line(record: InstructorRecord) -> bytes:
    name = type(record).__name__
    if name not in RECORD_TYPES:
        raise TypeError(f"not an instructor record: {name}")
    return b'{"record":' + canonical_bytes(record) + b',"type":"' + name.encode("ascii") + b'"}'
