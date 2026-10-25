"""Where each mark's snapshot is in Drive (story A16, judge 108 addendum 3, orchestrator decision 39).

Every copy is saved under its own content-addressed name (`nifty_<day>_<HHMM>_<SHA-256 first 16>.json.gz`), so two
overlapping runs never write one name: Drive's look-up-then-create cannot race into two files of one name, and no
clean-up step is needed. Which copy a mark uses is the one its ledger row names; readers never resolve a bare name.
- A run that took the mark writes a row naming its own copy; if two runs both did, the row first pushed to GitHub
  wins (the committer's same-file rule) and the other copy stays in Drive, unused and harmless.
- A due mark with no row but copies in Drive (a run stored its copy, then died before its row) gets a row naming the
  copy with the smallest name: a fixed rule, so every settlement picks the same one."""

from __future__ import annotations

from datetime import date, datetime

from ..storage.raw_store import RawFileStore
from .document import mark_prefix, snapshot_folder, snapshot_path, utc_text
from .ledger import SlotLedger


class SnapshotFiles:
    def __init__(self, source: str, store: RawFileStore, ledger: SlotLedger):
        self.source, self.store, self.ledger = source, store, ledger

    def save(self, day: date, mark: datetime, data: bytes) -> str:
        """Saves a copy under its own name; returns its path (the same bytes again change nothing)."""
        path = snapshot_path(self.source, day, mark, data)
        self.store.put(path, data)
        return path

    def used(self, day: date, mark: datetime) -> str | None:
        """The path the mark's ledger row names (None: no row, or a row with no file: missed or failed)."""
        key = utc_text(mark)
        row = next((r for r in self.ledger.rows(day) if r["mark"] == key), None)
        return row["raw_path"] or None if row else None

    def unrowed_copy(self, day: date, mark: datetime) -> str | None:
        """The copy a due mark without a row uses: the smallest name among the mark's copies in Drive, or None."""
        folder = snapshot_folder(self.source, day)
        try:
            names = self.store.checksums(folder)
        except NotImplementedError:
            return None  # a store that cannot list: the mark stays missed (stated in the story)
        prefix = mark_prefix(day, mark)
        found = sorted(name for name in names if name.startswith(prefix))
        return f"{folder}/{found[0]}" if found else None

    def read(self, path: str | None) -> bytes | None:
        return self.store.get(path) if path else None
