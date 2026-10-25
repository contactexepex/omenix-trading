"""Book 1's decisions of the day as a candidate source (story REC1b, section 5): `complete` only when the run log
names the day's decision run and every file of that run matches its `records.sha256` line. A step that failed, was
refused or never ran makes the source unavailable with that status; a file whose hash differs is an input failure."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from ..constants import BOOK1_RULES, Decision
from ..desk.run_log import RunLog, book_results
from ..playbook.opportunities import BOOK
from .constants import CandidateSourceName, SourceState
from .contracts import CandidateSource
from .ports import CandidateSourcePort, InputFailed, SeenDecision, SourceReading, open_run_log
from .refs import RecordRef

DECISIONS_STEP = "decisions"
MANIFEST = "records.sha256"
NOT_DECISIONS = {MANIFEST, "inputs.json"}  # the run's own files that are not decisions
NO_RUN = "{status}, {why}"
BAD_HASH = "{path}: its SHA-256 is not the one in records.sha256"
NOT_LISTED = "{path}: not in records.sha256"
MISSING_FILE = "{path}: listed in records.sha256 but missing"
UNREADABLE = "{path}: not a readable decision record ({kind})"


class DeskSource(CandidateSourcePort):
    name = CandidateSourceName.DESK_BOOK1

    def __init__(self, root: Path, journal: Path, book: str = BOOK1_RULES):
        """`journal`: the folder that holds `<book>/decisions/<day>/<run>/`."""
        self.root, self.journal, self.book = root, journal, book

    def read(self, day: date) -> SourceReading:
        log = open_run_log(self.root, day)
        entry = book_results(log.result(DECISIONS_STEP)).get(self.book) if log.done(DECISIONS_STEP) else None
        if not entry or "run_id" not in entry:
            return _unavailable(_why_not(log))
        folder = self.journal / self.book / "decisions" / day.isoformat() / entry["run_id"]
        listed = _manifest(folder)
        if missing := sorted(set(listed) - {p.name for p in folder.iterdir()}):  # both ways: none may be missing
            raise InputFailed(MISSING_FILE.format(path=(folder / missing[0]).relative_to(self.root).as_posix()))
        decisions = tuple(_decision(self.root, path, listed) for path in sorted(folder.glob("*.json"))
                          if path.name not in NOT_DECISIONS)  # fmt: skip
        source = CandidateSource(self.name, SourceState.COMPLETE, None)
        return SourceReading(source, decisions, (_ref(self.root, folder / MANIFEST),))


def _why_not(log: RunLog) -> str:
    if not log.done(DECISIONS_STEP):
        return NO_RUN.format(status="missing", why="the decisions step is not in the run log")
    result = log.result(DECISIONS_STEP)
    return NO_RUN.format(status=result.get("status", "ok"), why=result.get("reason", "no Book 1 decision run"))


def _unavailable(status: str) -> SourceReading:
    return SourceReading(CandidateSource(CandidateSourceName.DESK_BOOK1, SourceState.UNAVAILABLE, status), (), ())


def _manifest(folder: Path) -> dict[str, str]:
    try:
        lines = (folder / MANIFEST).read_text(encoding="utf-8").splitlines()
    except OSError as missing:
        raise InputFailed(f"{folder.name}/{MANIFEST}: {type(missing).__name__}") from None
    return {name: digest for digest, name in (line.split(maxsplit=1) for line in lines if line.strip())}


def _decision(root: Path, path: Path, listed: dict[str, str]) -> SeenDecision:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    relative = path.relative_to(root).as_posix()
    if path.name not in listed:
        raise InputFailed(NOT_LISTED.format(path=relative))
    if listed[path.name] != digest:
        raise InputFailed(BAD_HASH.format(path=relative))
    try:
        record = json.loads(data)
        version = record.get("version_id") or record["book"]  # a book's day record with no version names the book
        traded = record["decision"]["outcome"] == Decision.CHOSEN and record["mode"] == BOOK
    except (ValueError, KeyError, TypeError) as bad:
        raise InputFailed(UNREADABLE.format(path=relative, kind=type(bad).__name__)) from None
    return SeenDecision(version, RecordRef(relative, digest), traded)  # a shadow's "trade" is never in the book


def _ref(root: Path, path: Path) -> RecordRef:
    return RecordRef(path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
