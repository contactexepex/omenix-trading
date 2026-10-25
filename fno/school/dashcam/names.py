"""Where the dashcam's files live: one Drive path per (session, slot, kind), one counts file per session and slot."""

import re
from datetime import date
from pathlib import PurePosixPath

from ..constants import RecordKind

SCHOOL_AREA = "school"  # the folder under the data area that holds every school file (and its receipts)
DASHCAM_FOLDER = f"{SCHOOL_AREA}/dashcam"
COUNTS_FOLDER = "research/school/counts"  # in the repository: public counts only, never a contract or a price
SLOT_FILE_SUFFIX = "jsonl.gz"
COUNTS_SUFFIX = "csv"


def slot_file_path(session: date, slot: str, kind: RecordKind) -> str:
    """Relative to the data store's area, e.g. `school/dashcam/2026/11/02/1500.decisions.jsonl.gz`."""
    return f"{DASHCAM_FOLDER}/{session:%Y/%m/%d}/{slot.replace(':', '')}.{kind}.{SLOT_FILE_SUFFIX}"


def counts_path(session: date, slot: str) -> PurePosixPath:
    if not re.fullmatch(r"\d\d:\d\d", slot):
        raise ValueError(f"not a slot time: {slot!r}")
    return PurePosixPath(COUNTS_FOLDER, f"{session:%Y/%m}", f"{session:%Y%m%d}_{slot.replace(':', '')}.{COUNTS_SUFFIX}")
