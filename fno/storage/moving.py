"""Moving a repository file into its receipt-backed Drive series (O9b, section 2 step 1): the file's bytes become the
series' first file and the series, read back through the verified cache, must give the same bytes. Moving again is a
no-op when Drive already holds those bytes; Drive holding other bytes stops the move (the file and Drive disagree:
a person decides, nothing is overwritten)."""

from __future__ import annotations

import hashlib

from .receipted_rows import ReceiptedRowLog, ReceiptedSnapshots

MOVED = "{name}: moved to Drive and read back equal ({size} bytes, SHA-256 {sha})"
ALREADY = "{name}: already in Drive, equal ({size} bytes, SHA-256 {sha})"
DIFFERS = "{name}: Drive already holds other bytes ({drive} bytes against the file's {size}); nothing written"
UNEQUAL = "{name}: read back unequal after the move ({drive} bytes against {size}); stop and look"


class MoveRefused(RuntimeError):
    """The file and its Drive series disagree: the move stops, nothing is overwritten."""


def move_into(series: ReceiptedRowLog | ReceiptedSnapshots, data: bytes, name: str) -> str:
    """One line saying what happened; MoveRefused when Drive holds, or gives back, other bytes."""
    facts = {"name": name, "size": len(data), "sha": hashlib.sha256(data).hexdigest()}
    current = series.current_bytes()
    if current == data:
        return ALREADY.format(**facts)
    if current:
        raise MoveRefused(DIFFERS.format(drive=len(current), **facts))
    series.write_bytes(data)
    back = series.current_bytes()
    if back != data:
        raise MoveRefused(UNEQUAL.format(drive=len(back), **facts))
    return MOVED.format(**facts)
