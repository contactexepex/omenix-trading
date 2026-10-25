"""The school's position records beside E1's ledger (story MS-P1d): one canonical JSON line per recorded
`LedgerEntry`, appended durably with E1's own file helpers. E1's ledger holds the cash and units; this file holds what
the laws read and E1 does not keep: each position's road, structure, legs, lot, entry day and maximum loss.

One entry per (position, open or close): the same entry again is a no-op; a different entry under the same key is
refused, so a fill is never recorded twice or rewritten."""

import json
from pathlib import Path

from ...books.files import append_durably, complete_lines, drop_partial_line
from ..contracts.accounts import LedgerEntry
from ..contracts.codec import canonical_bytes, from_plain
from ..contracts.decisions import OpenPosition


class EntryConflict(RuntimeError):
    """A position's opening or closing is already recorded with different content."""


class PositionBook:
    def __init__(self, path: Path):
        self.path = Path(path)

    def entries(self) -> list[LedgerEntry]:
        if not self.path.exists():
            return []
        lines = complete_lines(self.path.read_text(encoding="utf-8")).splitlines()
        return [from_plain(LedgerEntry, json.loads(line)) for line in lines if line]

    def check(self, entry: LedgerEntry) -> bool:
        """True when this exact entry is already recorded (a retry); refuses a different entry under the same key, a
        close of a position not open, and a position ID reused for another position."""
        pid = entry.position.position_id
        for held in self.entries():
            if _key(held) == _key(entry):
                if canonical_bytes(held) == canonical_bytes(entry):
                    return True
                raise EntryConflict(f"{pid}: its {_kind(entry)} is already recorded differently")
        if entry.closes and entry.position not in self.open_positions():
            raise EntryConflict(f"{pid}: a close of a position that is not open as recorded")
        return False

    def add(self, entry: LedgerEntry) -> bool:
        """True when appended; False when this exact entry is already recorded."""
        if self.check(entry):
            return False
        if self.path.exists():
            drop_partial_line(self.path)  # a line cut short by a crash is never data
        append_durably(self.path, canonical_bytes(entry).decode("utf-8") + "\n")
        return True

    def opened(self) -> list[OpenPosition]:
        return [e.position for e in self.entries() if not e.closes]

    def open_positions(self) -> list[OpenPosition]:
        closed = {e.position.position_id for e in self.entries() if e.closes}
        return [p for p in self.opened() if p.position_id not in closed]


def _key(entry: LedgerEntry) -> tuple[str, bool]:
    return entry.position.position_id, entry.closes


def _kind(entry: LedgerEntry) -> str:
    return "closing" if entry.closes else "opening"
