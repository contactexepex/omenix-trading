"""The SHA-256 of G13b's method files and those it imports (G13's method, G7's EWMA and series), carried by every
record: a changed method is a new hash, never a quiet change. Commands, stores, readers and wiring are left out."""

from __future__ import annotations

from pathlib import Path

from ..price_distribution.method import FNO
from ..price_distribution.method import METHOD_FILES as G13_FILES
from ..price_distribution.method import method_sha256 as files_sha256

PACKAGE = Path(__file__).resolve().parent
OWN = ("bhavcopy_chains", "build", "closes", "constants", "forecasters", "records", "t4")
METHOD_FILES = (*(PACKAGE / f"{name}.py" for name in OWN), *G13_FILES,
                FNO / "forecast_v4_rules" / "baselines.py", FNO / "forecast_v4_rules" / "series.py")  # fmt: skip


def method_sha256() -> str:
    return files_sha256(METHOD_FILES)
