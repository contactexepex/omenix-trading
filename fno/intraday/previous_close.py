"""The previous session's 15:30 level for a session's overnight return (story A16b), read from the very 15-minute copy
the previous row names, so the run and `backfill-verify` take the same value: one rule, written once."""

from __future__ import annotations

from .candle_archive import CandleArchive, CopyDamaged
from .session_deriver import SessionDeriver


class PreviousClose:
    def __init__(self, archive: CandleArchive, deriver: SessionDeriver):
        self.archive, self.deriver = archive, deriver

    def of(self, previous_row: dict) -> float | None:
        """None when the previous row's levels are untrusted; CopyDamaged when its copy is not in the manifest or
        Drive, or differs from its manifest row."""
        manifest_row = self.archive.row_for(previous_row["copy_15m"])
        if manifest_row is None:
            raise CopyDamaged(f"{previous_row['copy_15m']}: no manifest row")
        return self.deriver.last_level(previous_row, self.archive.load(manifest_row))
