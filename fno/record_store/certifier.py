"""The certifier (story DR1): reads every version of a session, checks its integrity (the bytes match the SHA-256
saved with them) and the dataset's checks for the level, lets the rules choose one version among those that pass and
writes the record. No version passing, or no choice, means no record and a named reason: a reader that needs the
record stops (owner, 23 Oct 2026: "We don't have to run the forecasting until we get a proper quality data")."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from ..storage.raw_store import RawFileStore
from . import publisher
from .constants import (
    ALREADY,
    CERTIFIED_LINE,
    CONFLICT,
    INTEGRITY,
    NO_VERSIONS,
    NONE_PASSED,
    NOT_CERTIFIED,
    NOT_PUSHED,
    UNREADABLE_LINE,
)
from .models import CheckResult, Record, Verdict
from .record_folder import RecordFolder, chosen_in
from .rules import DatasetRules, SourceUnreadable
from .staging import VersionSource


@dataclass(frozen=True)
class Outcome:
    recorded: bool
    line: str
    record: Record | None = None
    alert: bool = False  # a record not on origin's main, or a conflict: #fno-desk is told


class Certifier:
    def __init__(self, rules: DatasetRules, versions: VersionSource, drive: RawFileStore, records: RecordFolder,
                 note: Callable[[str, Record], str] | None = None):  # fmt: skip
        """`drive`: reads each version by its path; `note`: an extra word for the line (the shadow's comparison)."""
        self.rules, self.versions, self.drive, self.records, self.note = rules, versions, drive, records, note

    def certify(self, session: str, level: str) -> Outcome:
        name = self.rules.name
        held = self.records.chosen(name, session, level)
        if held is not None:  # recorded here before: it counts once origin's main holds it (a refused push is retried)
            line = ALREADY.format(dataset=name, session=session, level=level, sha=held.sha256[:12])
            return self._published(session, level, held.sha256, Outcome(True, line))
        try:
            return self._certify(session, level)
        except SourceUnreadable as unreadable:  # never an ordinary NOT recorded: exit 1 and #fno-desk
            line = UNREADABLE_LINE.format(dataset=name, session=session, level=level, why=unreadable)
            return Outcome(False, line, alert=True)

    def _certify(self, session: str, level: str) -> Outcome:
        verdicts, passing = [], []
        for version in self.versions.versions(session):
            data, problem = self._bytes(version)
            checks = self._checks(session, level, version.sha256, data, problem)
            verdicts.append(Verdict(version, tuple(checks)))
            if verdicts[-1].passed:
                passing.append((version, data))
        if not verdicts:
            return self._refused(session, level, NO_VERSIONS)
        if not passing:
            failures = "; ".join(f"{v.version.path.rsplit('/', 1)[-1]}: {v.failure()}" for v in verdicts)
            return self._refused(session, level, NONE_PASSED.format(failures=failures))
        choice = self.rules.choose(session, level, passing)
        if choice.version is None:
            return self._refused(session, level, choice.reason)
        record = Record(
            self.rules.name, session, level, choice.version, choice.reason, self.rules.version, tuple(verdicts)
        )
        return self._written(record, len(passing), len(verdicts))

    def _checks(self, session: str, level: str, sha256: str, data: bytes | None, problem: str) -> list[CheckResult]:
        if data is None:
            return [CheckResult(INTEGRITY, False, problem)]
        if hashlib.sha256(data).hexdigest() != sha256:
            return [CheckResult(INTEGRITY, False, "bytes differ from their receipt")]
        return [CheckResult(INTEGRITY, True), *self.rules.checks(session, level, data)]

    def _bytes(self, version) -> tuple[bytes | None, str]:
        try:
            data = self.drive.get(version.path)
        except Exception as failure:  # noqa: BLE001 - an unreadable version fails its integrity check, never the run
            return None, f"unreadable ({type(failure).__name__})"
        return data, "" if data is not None else "not in Drive"

    def _written(self, record: Record, passed: int, total: int) -> Outcome:
        name, session, level, sha = record.dataset, record.session, record.level, record.chosen.sha256
        held = self.records.write(record)
        if held.sha256 != sha:
            return self._conflict(session, level, held.sha256, sha)
        reason = record.reason + (f"; {self.note(session, record)}" if self.note else "")
        line = CERTIFIED_LINE.format(dataset=name, session=session, level=level, sha=sha[:12], passed=passed,
                                     total=total, reason=reason)  # fmt: skip
        return self._published(session, level, sha, Outcome(True, line, record))

    def _published(self, session: str, level: str, sha: str, done: Outcome) -> Outcome:
        published = self.records.publish(self.rules.name, session, level)
        if published is None or published.state == publisher.PUSHED:
            return done
        if published.state == publisher.CONFLICT:
            return self._conflict(session, level, chosen_in(published.held).sha256, sha)
        line = NOT_PUSHED.format(dataset=self.rules.name, session=session, level=level, why=published.detail)
        return Outcome(False, line, done.record, alert=True)

    def _conflict(self, session: str, level: str, held: str, sha: str) -> Outcome:
        line = CONFLICT.format(dataset=self.rules.name, session=session, level=level, held=held[:12], sha=sha[:12])
        return Outcome(False, line, alert=True)

    def _refused(self, session: str, level: str, reason: str) -> Outcome:
        line = NOT_CERTIFIED.format(dataset=self.rules.name, session=session, level=level, reason=reason)
        return Outcome(False, line)
