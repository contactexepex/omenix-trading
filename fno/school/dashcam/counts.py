"""The public counts file (story 3.4, privacy): how many decisions ended in each outcome per road and driver for one
session and slot. Codes and whole numbers only, never a contract, a strike, a price or a card internal (E2c's rule).
Write-once like every record: the same text again is a no-op, other text is a replay conflict.

Assumption: one process writes a session's counts file (the fleet's single runner, MS-P1j, which also commits it). The
exists-then-write below is not atomic, so two concurrent writers with different counts could overwrite each other."""

import csv
import io
from collections import Counter
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from ..contracts.dashcam import ReplayConflict
from ..contracts.records import DecisionRecord
from ..contracts.slot_file import SlotRecord
from .names import counts_path

HEADER = ("session", "slot", "road", "driver", "outcome", "reason", "count")
COUNTS_CHANGED = "rule broken: {path} holds other counts than these; a counts file is never rewritten"


def count_rows(session: date, slot: str, records: Iterable[SlotRecord]) -> list[tuple]:
    """One row per (road, driver, outcome, reason), sorted, from the decision records of the slot."""
    tally = Counter(
        (r.road.value, r.decision.driver_id, r.decision.outcome.value, r.decision.reason)
        for r in records
        if isinstance(r, DecisionRecord) and r.session == session and r.slot == slot
    )
    return [(session.isoformat(), slot, *key, n) for key, n in sorted(tally.items())]


def counts_text(rows: Iterable[tuple]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    return out.getvalue()


class PublicCountsFile:
    def __init__(self, root: Path):
        self.root = Path(root)

    def write(self, session: date, slot: str, records: Iterable[SlotRecord]) -> Path:
        relative = counts_path(session, slot)
        file, text = self.root / relative, counts_text(count_rows(session, slot, records))
        if file.is_file():
            if file.read_text() != text:
                raise ReplayConflict(COUNTS_CHANGED.format(path=relative))
            return file
        file.parent.mkdir(parents=True, exist_ok=True)
        temporary = file.with_name(f".{file.name}.part")
        temporary.write_text(text)
        temporary.replace(file)
        return file
