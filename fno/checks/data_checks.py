"""Data checks before every decision (story C3, design 9): the desk confirms its data is present, fresh and consistent
before any new trade. Each check is one class behind `DataCheck`; a failure names the check and why. Any failure means
"no new trade: stale or unverified data" with an alert. A failure of a check marked `prices_unverified` also means the
snapshot's prices may not be used at all: due exits become pending exits, filled at the next valid quotes (E4's exit
path). Other failures (a missing NSE file of the previous session) stop new trades only: risk-reducing exits still run
at valid quotes (design 9)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from ..constants import DATA_UNVERIFIED
from ..desk.common_pack import CommonPack
from ..desk.snapshot import ContractKey, ExecutionSnapshot

FAILED = "{check}: {reason}"


@dataclass(frozen=True)
class CaptureRecord:
    """A committed, hashed record of one quote capture: its ID, the SHA-256 of its quote file and of its sidecar (which
    holds the capture times), and where the record is committed. The snapshot read for a decision must be this one."""

    snapshot_id: str
    csv_sha256: str
    meta_sha256: str
    source: str


@dataclass(frozen=True)
class ScheduledCapture:
    """The quote capture a decision executes at, the window it must be taken in (times IST-aware), and its committed
    capture record (None when nothing records it)."""

    snapshot_id: str
    start: datetime
    end: datetime
    record: CaptureRecord | None


@dataclass(frozen=True)
class CheckSubject:
    pack: CommonPack  # E2's common market pack of the day
    capture: ScheduledCapture | None  # None when nothing names the day's capture
    snapshot: ExecutionSnapshot | None  # None when it could not be read
    unreadable: str  # why there is no snapshot; empty when there is one
    legs: tuple[ContractKey, ...]  # the legs the decision needs (none for an exit review)

    @property
    def day(self) -> date:
        return self.pack.day


@dataclass(frozen=True)
class Failure:
    check: str
    reason: str
    prices_unverified: bool

    def __str__(self) -> str:
        return FAILED.format(check=self.check, reason=self.reason)


@dataclass(frozen=True)
class CheckReport:
    day: date
    snapshot_id: str  # the capture checked; empty when none was named
    legs: tuple[ContractKey, ...]  # the legs whose quotes were checked
    failures: tuple[Failure, ...]

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def prices_unverified(self) -> bool:
        """The snapshot's prices may not be used, for exits either."""
        return any(f.prices_unverified for f in self.failures)

    def reason(self) -> str:
        return f"{DATA_UNVERIFIED}: " + "; ".join(str(f) for f in self.failures)

    def price_reason(self) -> str:
        return f"{DATA_UNVERIFIED}: " + "; ".join(str(f) for f in self.failures if f.prices_unverified)


class DataCheck(ABC):
    name: str
    prices_unverified: bool  # a failure makes the snapshot's prices unusable, exits included

    @abstractmethod
    def problems(self, subject: CheckSubject) -> list[str]:
        """Why the data fails this check; empty when it passes."""


class DataChecks:
    def __init__(self, checks: Sequence[DataCheck]):
        self.checks = tuple(checks)

    def run(self, subject: CheckSubject) -> CheckReport:
        failures = tuple(
            Failure(check.name, problem, check.prices_unverified)
            for check in self.checks
            for problem in check.problems(subject)
        )
        snapshot_id = subject.capture.snapshot_id if subject.capture else ""
        return CheckReport(subject.day, snapshot_id, subject.legs, failures)

    @staticmethod
    def require_for(report: CheckReport, snapshot: ExecutionSnapshot, legs: Sequence[ContractKey] = ()) -> None:
        """A report on another snapshot, or one that did not check every needed leg, is a wiring error: the desk
        never acts on unchecked data."""
        if (report.day, report.snapshot_id) != (snapshot.day, snapshot.snapshot_id):
            raise ValueError(f"data checks ran on {report.snapshot_id} of {report.day}, not {snapshot.snapshot_id}")
        unchecked = [leg for leg in legs if leg not in report.legs]
        if unchecked:
            raise ValueError(f"data checks did not check the quotes of {unchecked}")
