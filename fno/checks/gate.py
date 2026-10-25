"""The data gate before every decision (story C3): reads the scheduled capture, runs every data check on it and the
common pack, and alerts #fno-desk when any fails. Entries are refused on any failure; exits use the report to wait for
valid quotes when the prices are unverified (E4's exit path)."""

from __future__ import annotations

from collections.abc import Sequence

from ..alerts.sender import AlertSender
from ..desk.common_pack import CommonPack
from ..desk.snapshot import ContractKey, ExecutionSnapshot, ExecutionSnapshotSource, SnapshotError
from .data_checks import CheckReport, CheckSubject, DataChecks
from .schedule import ExecutionSchedule

ALERT = "F&O paper desk {day} ({snapshot}): {reason}"
WAITING_EXITS = "; exits due, waiting for a readable snapshot: {trades}"


class DataGate:
    def __init__(
        self, checks: DataChecks, snapshots: ExecutionSnapshotSource, schedule: ExecutionSchedule, alerts: AlertSender
    ):
        self.checks, self.snapshots, self.schedule, self.alerts = checks, snapshots, schedule, alerts
        self.sent: set[str] = set()  # one alert per distinct text: the daily run checks the same data several times

    def check(self, pack: CommonPack, legs: Sequence[ContractKey] = (),
              due_exits: Sequence[str] = ()) -> tuple[ExecutionSnapshot | None, CheckReport]:  # fmt: skip
        """The day's execution snapshot (None when it cannot be read) and the checks' report on it, for these legs.
        `due_exits` (the exit desk's `due_exits`) are named in the alert when no snapshot can be read: those exits
        cannot be recorded as pending without one, so the alert is where they show."""
        capture = self.schedule.capture(pack)
        snapshot, unreadable = None, ""
        if capture is not None:
            try:
                snapshot = self.snapshots.snapshot(pack.day, capture.snapshot_id)
            except SnapshotError as problem:
                unreadable = str(problem)
        report = self.checks.run(CheckSubject(pack, capture, snapshot, unreadable, tuple(legs)))
        if not report.ok:
            name = capture.snapshot_id if capture else "no capture"
            waiting = WAITING_EXITS.format(trades=", ".join(due_exits)) if snapshot is None and due_exits else ""
            text = ALERT.format(day=pack.day, snapshot=name, reason=report.reason()) + waiting
            if text not in self.sent:
                self.sent.add(text)
                self.alerts.send(text)
        return snapshot, report
