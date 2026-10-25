"""What story DR1 keeps: a staged version, the result of one check, a record and an as-seen pointer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class StagedVersion:
    path: str  # Drive path, area included
    sha256: str
    size: int
    fetched_at: str  # when the bytes were saved (the receipt's time, UTC ISO 8601)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str = ""  # why it failed; never a data value


@dataclass(frozen=True)
class Verdict:
    version: StagedVersion
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def failure(self) -> str:
        failed = next(check for check in self.checks if not check.passed)
        return f"{failed.name}: {failed.detail}"


@dataclass(frozen=True)
class Record:
    dataset: str
    session: str  # ISO date
    level: str
    chosen: StagedVersion
    reason: str
    rules: str  # the dataset rules' version
    verdicts: tuple[Verdict, ...] = field(default=())

    def to_document(self) -> dict:
        """Deterministic: the same choice gives the same bytes (no clock), so a rerun is a no-op."""
        return {
            "dataset": self.dataset, "session": self.session, "level": self.level, "chosen": asdict(self.chosen),
            "reason": self.reason, "rules": self.rules,
            "versions": [{**asdict(v.version), "checks": [asdict(c) for c in v.checks]} for v in self.verdicts],
        }  # fmt: skip


@dataclass(frozen=True)
class AsSeen:
    """What a decision used: the record's level and the exact bytes' SHA-256."""

    dataset: str
    session: str
    level: str
    path: str
    sha256: str
