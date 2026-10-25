"""The instructor's public counts file (story MS-INS, part e; E2c's privacy rule): how many closed trades and tickets
of each driver and road got each primary cause and modifier in one session. Codes and whole numbers only: no rupee,
contract, strike, price or card internal. Write-once: the same text again is a no-op, other text is refused. The
fleet's runner (MS-P1j) commits it with the session's other public files (agreed with j's builder, 23 Oct 2026)."""

import csv
import io
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path, PurePosixPath

from ..contracts import Classification
from ..ports import InstructorConflict

COUNTS_FOLDER = "research/school/counts/instructor"  # inside MS-P1j's counts folder: one commit takes both
HEADER = ("session", "driver", "road", "ticket", "primary", "modifier", "count")
UNCLASSIFIED = "unclassified"
CHANGED = "{path} holds other counts than these; a counts file is never rewritten"


def counts_path(session: date) -> PurePosixPath:
    return PurePosixPath(COUNTS_FOLDER, f"{session:%Y/%m}", f"{session:%Y%m%d}.csv")


def counts_text(session: date, records: Iterable[Classification]) -> str:
    tally = Counter((r.driver_id, r.road.value, "yes" if r.is_ticket else "no", r.primary or UNCLASSIFIED,
                     r.modifier.value) for r in records if not r.corrects)  # fmt: skip
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows((session.isoformat(), *key, n) for key, n in sorted(tally.items()))
    return out.getvalue()


class InstructorCountsFile:
    def __init__(self, root: Path):
        self.root = Path(root)

    def write(self, session: date, records: Iterable[Classification]) -> Path:
        relative = counts_path(session)
        file, text = self.root / relative, counts_text(session, records)
        if file.is_file():
            if file.read_text() != text:
                raise InstructorConflict(CHANGED.format(path=relative))
            return file
        file.parent.mkdir(parents=True, exist_ok=True)
        temporary = file.with_name(f".{file.name}.part")
        temporary.write_text(text)
        temporary.replace(file)
        return file
