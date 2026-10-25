"""The repository folders M1's weather step writes (asked by the daily run, story O1): its records and its two
forecasters' v4 rows (G7's writer). O1 commits exactly these, so the weather step never commits another step's files,
nor another step its own. Kept outside `wiring.py`, which M1's method hash covers, so naming the folders never changes
a record's `method_sha256`."""

from __future__ import annotations

from ..config import ROOT
from ..forecast_v4_rules.wiring import V4_FOLDER
from .day import FORECASTERS
from .wiring import WEATHER_FOLDER


def record_folders() -> tuple[str, ...]:
    """Repository-relative, each ending in "/"."""
    folders = (WEATHER_FOLDER, *(V4_FOLDER / name for name in FORECASTERS))
    return tuple(f"{folder.relative_to(ROOT).as_posix()}/" for folder in folders)
