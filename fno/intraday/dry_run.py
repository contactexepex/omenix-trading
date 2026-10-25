"""Where a dry run may write (stories A16 and A16b): only outside the repository, so raw quotes and candles never land
in it."""

from __future__ import annotations

from pathlib import Path


def inside_repository(folder: Path) -> bool:
    from ..storage.wiring import REPOSITORY

    return folder.resolve().is_relative_to(REPOSITORY.resolve())
