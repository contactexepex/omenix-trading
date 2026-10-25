"""The practice dashcam (story MS-SIM-d2, criterion 15; orchestrator, 22 Oct: the label is in the record itself).

A replay dashcam that writes each record line with the practice label beside the record: `{"label": ..., "record": ...,
"type": ...}`. `decode_slot_file` ignores the extra key, so a plain reader still reads the file, and `labels` reads the
label back. Files go under the practice folder and are never pushed; the seals say so (`replay`)."""

import gzip
import json

from ...contracts.codec import canonical_bytes
from ...contracts.slot_file import RECORD_TYPES, SlotRecord
from ...fleet.replay_store import ReplayDashcam
from ..constants import PRACTICE_LABEL

DASHCAM_HOME = "dashcam"  # inside each scenario's home: where its practice dashcam files are


class PracticeDashcam(ReplayDashcam):
    def encode(self, records: tuple[SlotRecord, ...]) -> bytes:
        lines = [_line(record) for record in records]
        return gzip.compress(b"".join(line + b"\n" for line in lines), mtime=0)


def _line(record: SlotRecord) -> bytes:
    name = type(record).__name__
    if name not in RECORD_TYPES:
        raise TypeError(f"not a dashcam record: {name}")
    label = json.dumps(PRACTICE_LABEL).encode("ascii")
    return b'{"label":' + label + b',"record":' + canonical_bytes(record) + b',"type":"' + name.encode("ascii") + b'"}'


def labels(data: bytes) -> list[str | None]:
    """The label on each stored line (None where a line has none)."""
    return [json.loads(line).get("label") for line in gzip.decompress(data).splitlines() if line]
