"""The checks on the execution snapshot itself (story C3): it can be read (present, the day's, its file matching the
hash in its own sidecar), it was captured inside its scheduled window (the capture times in its sidecar), and it is
the capture its committed capture record names (judge 81 ruling 2). A failure of any makes its prices unusable."""

from __future__ import annotations

from .data_checks import CheckSubject, DataCheck

TIME = "%H:%M:%S"


class SnapshotReadable(DataCheck):
    name, prices_unverified = "snapshot", True

    def problems(self, subject: CheckSubject) -> list[str]:
        if subject.capture is None:
            return [f"no execution capture is named for {subject.day}"]
        return [subject.unreadable] if subject.snapshot is None else []


class SnapshotInWindow(DataCheck):
    """Freshness is the capture's own times from its sidecar; a quote's age is never claimed (A4)."""

    name, prices_unverified = "snapshot window", True

    def problems(self, subject: CheckSubject) -> list[str]:
        snapshot, capture = subject.snapshot, subject.capture
        if snapshot is None or capture is None:
            return []
        if capture.start <= snapshot.started_at and snapshot.finished_at <= capture.end:
            return []
        return [
            f"{snapshot.snapshot_id} was captured {snapshot.started_at:{TIME}}-{snapshot.finished_at:{TIME}}, "
            f"outside its window {capture.start:{TIME}}-{capture.end:{TIME}} (stale or early)"
        ]


class SnapshotMatchesRecord(DataCheck):
    """The snapshot read is the one its committed capture record names: same ID, quote file and sidecar (so the same
    capture times). A file swapped or rewritten after the record was committed is refused."""

    name, prices_unverified = "capture record", True

    def problems(self, subject: CheckSubject) -> list[str]:
        snapshot, capture = subject.snapshot, subject.capture
        if snapshot is None or capture is None:
            return []
        record = capture.record
        if record is None:
            return [f"no committed capture record names {snapshot.snapshot_id}"]
        found = [
            f"{what} {mine} differs from the record's {theirs} ({record.source})"
            for what, mine, theirs in (
                ("snapshot", snapshot.snapshot_id, record.snapshot_id),
                ("quote file hash", snapshot.sha256, record.csv_sha256),
                ("sidecar hash", snapshot.meta_sha256, record.meta_sha256),
            )
            if mine != theirs
        ]
        return [f"{snapshot.snapshot_id}: " + "; ".join(found)] if found else []
