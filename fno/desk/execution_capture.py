"""The execution snapshot (story E3): a second recorder capture at about 15:15, by A4's own rules, with its own ID and
hash, and its committed capture record (judge 81 ruling 2): `journal/execution/<date>/<snapshot_id>.json` holds the
capture ID, its times and the SHA-256 of its quote file and sidecar. C3's data checks read the day's latest record
through `ExecutionSchedule`, so every timely decision of the day is checked and filled against that one capture."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from ..checks.data_checks import CaptureRecord, ScheduledCapture
from ..checks.schedule import ExecutionSchedule
from ..constants import JOURNAL_FOLDER
from ..quotes.recorder import QuoteSnapshotRecorder, RecordResult
from ..storage.raw_store import RawFileStore
from .common_pack import CommonPack
from .daily_ports import Committer, ExecutionCapture
from .timetable import Timetable

EXECUTION_FOLDER = "execution"


def records_folder(root: Path, day: date) -> Path:
    return Path(root) / JOURNAL_FOLDER / EXECUTION_FOLDER / day.isoformat()


class RecorderExecutionCapture(ExecutionCapture):
    def __init__(self, take: Callable[[], RecordResult], quotes: RawFileStore, quotes_folder: Path, root: Path,
                 committer: Committer):  # fmt: skip
        self.take, self.quotes, self.quotes_folder, self.root, self.committer = (
            take, quotes, Path(quotes_folder), Path(root), committer)  # fmt: skip

    def capture(self, day: date) -> CaptureRecord | None:
        result = self.take()
        if not result.snapshot_id:
            return None
        csv_name, meta_name = (
            QuoteSnapshotRecorder.path(day, f"{result.snapshot_id}{suffix}") for suffix in (".csv", ".meta.json")
        )
        sidecar = self.quotes_folder / meta_name  # the quote file itself is in Drive only (A4b): never committed
        try:
            csv_bytes, meta_bytes = self.quotes.get(csv_name), self.quotes.get(meta_name)
        except Exception:  # not readable back from Drive: like an unsaved file, no record (the gate then alerts)
            csv_bytes = None
        if csv_bytes is None:  # not saved: the sidecar says why; no record, so nothing is checked or filled from it
            self.committer.commit((sidecar,), f"Execution capture {day}: quote file not saved")
            return None
        meta = json.loads(meta_bytes)
        body = {"snapshot_id": result.snapshot_id, "started_at": meta["started_at"], "finished_at": meta["finished_at"],
                "complete": result.complete, "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
                "meta_sha256": hashlib.sha256(meta_bytes).hexdigest()}  # fmt: skip
        path = records_folder(self.root, day) / f"{result.snapshot_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        commit = self.committer.commit((path, sidecar), f"Execution capture {day}")
        return _record(body, f"{path.relative_to(self.root).as_posix()} in commit {commit}")


def _record(body: dict, source: str) -> CaptureRecord:
    return CaptureRecord(body["snapshot_id"], body["csv_sha256"], body["meta_sha256"], source)


class CommittedExecutionSchedule(ExecutionSchedule):
    """The day's latest committed execution capture record, in the window from the execution time to `fills_by`."""

    def __init__(self, root: Path, timetable: Timetable):
        self.root, self.timetable = Path(root), timetable

    def capture(self, pack: CommonPack) -> ScheduledCapture | None:
        bodies = [json.loads(p.read_text(encoding="utf-8")) for p in records_folder(self.root, pack.day).glob("*.json")]
        if not bodies:
            return None
        latest = max(bodies, key=lambda b: datetime.fromisoformat(b["started_at"]))
        times = self.timetable
        start, end = (times.at(pack.day, t) for t in (times.execution_snapshot, times.fills_by))
        source = f"{EXECUTION_FOLDER}/{pack.day}/{latest['snapshot_id']}.json"
        return ScheduledCapture(latest["snapshot_id"], start, end, _record(latest, source))
