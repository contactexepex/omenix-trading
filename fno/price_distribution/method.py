"""The SHA-256 of G13's method files, carried by every row (section 4): a changed method is a new hash, never a quiet
change. The commands, store and wiring are left out, so moving a file or a setting does not re-label the numbers."""

from __future__ import annotations

import hashlib
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
FNO = PACKAGE.parent
METHOD_FILES = tuple(PACKAGE / f"{name}.py" for name in (
    "build", "chain", "constants", "density", "forecasters", "forward", "horizons", "pricing", "records", "smile",
    "sources", "surface", "valuation",
)) + (FNO / "research_engine" / "implied_vol.py", FNO / "forecast" / "iv30.py", FNO / "analytics.py")  # fmt: skip


def method_sha256(files=METHOD_FILES) -> str:
    digest = hashlib.sha256()
    for file in files:
        digest.update(file.relative_to(FNO).as_posix().encode() + b"\0" + file.read_bytes() + b"\0")
    return digest.hexdigest()
