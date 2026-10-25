"""E3's 15:15 execution capture of a session, for the NIFTY drift diagnostic only (story 3.6): the day's latest
committed capture record (`journal/execution/<date>/<snapshot_id>.json`), read through E4's hash-checked snapshot
source. No record that day gives None, so every drift row says `drift_unknown`; a record whose quote file does not
match its hash is an error, never a quietly missing diagnostic."""

import json
from datetime import date
from pathlib import Path

from ...desk.execution_capture import records_folder
from ...desk.snapshot import ExecutionSnapshot, ExecutionSnapshotSource, SnapshotError


class RecordedCapture1515:
    def __init__(self, root: Path, snapshots: ExecutionSnapshotSource):
        self.root, self.snapshots = Path(root), snapshots

    def for_session(self, session: date) -> ExecutionSnapshot | None:
        folder = records_folder(self.root, session)
        records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
        if not records:
            return None
        latest = max(records, key=lambda record: record["finished_at"])
        snapshot = self.snapshots.snapshot(session, latest["snapshot_id"])
        if snapshot.sha256 != latest["csv_sha256"]:
            raise SnapshotError(f"{latest['snapshot_id']}: quote file differs from its committed capture record")
        return snapshot
