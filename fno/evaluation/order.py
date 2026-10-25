"""When a protocol version applies (story S1, criteria 1 and 3):
- **Freeze order:** the commit that added a version's freeze record must be a strict git ancestor of every book's
  first counted decision. A counted decision is a D3 run dated on or after the common start; earlier runs are pilot
  evidence.
- **Version of a decision:** a decision is counted under the latest protocol version whose freeze record's commit is
  a strict ancestor of the decision's own commit. With no such version it is not counted. If the decision's commit
  holds any of that version's targets changed (an edit to a frozen rule or file without a new version), it is refused
  (judge 85). A changed protocol is a new version with its own freeze, never an edit of a frozen one.
- **Verify:** the latest freeze's targets are unchanged in the working tree. A suite test runs it, so CI fails on any
  edit to a frozen target.
A run's commit is the one that added its `records.sha256` (D3). `verify` takes a protocol definition (story BR1a), S1's
by default; the freeze order and the version of a decision are S1's books' alone."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..playbook.decision_store import DecisionStore
from ..playbook.run_order import ordered_runs
from .definition import EVALUATION, ProtocolDefinition
from .freeze import AtCommit, WorkingTree, changed_targets, freeze_path, read_record

FREEZE_NAME = re.compile(r"^FREEZE_v([1-9][0-9]*)\.md$")


class ChangedAfterFreeze(RuntimeError):
    """A frozen target changed under the same protocol version: nothing is counted under it."""


@dataclass(frozen=True)
class CountedDecision:
    book: str
    run: str  # repository path of the run folder
    commit: str


def _strictly_before(git, older: str, newer: str) -> bool:
    return older != newer and git.is_ancestor(older, newer)


def freeze_commit(git, version: int) -> str | None:
    added = git.added_in(freeze_path(version))
    return added[0] if added else None


def frozen_versions(root: Path, definition: ProtocolDefinition = EVALUATION) -> list[int]:
    folder = Path(root) / Path(definition.freeze_path(1)).parent
    names = (FREEZE_NAME.match(p.name) for p in folder.glob("FREEZE_v*.md")) if folder.is_dir() else ()
    return sorted(int(m.group(1)) for m in names if m)


def first_counted_decision(root: Path, git, book: str, common_start: date | None) -> CountedDecision | None:
    """The book's earliest committed run dated on or after the common start (every run when none is given), in the
    shared run order (story D3b: commit time, then the run counter as a number). An uncommitted run is
    never first counted: it has no commit."""
    store = DecisionStore(root, book)
    days = sorted(p for p in store.folder.iterdir() if p.is_dir()) if store.folder.is_dir() else []
    for folder in days:
        day = date.fromisoformat(folder.name)
        if common_start is not None and day < common_start:
            continue
        for run in ordered_runs(root, store.runs(day), git):
            if run.commit is not None:
                return CountedDecision(book, run.path.relative_to(root).as_posix(), run.commit)
    return None


def order_problems(git, version: int, firsts: Sequence[CountedDecision]) -> list[str]:
    """Why version `version`'s freeze does not precede each book's first counted decision; empty when it does."""
    frozen = freeze_commit(git, version)
    if frozen is None and firsts:
        return [f"{freeze_path(version)} is not committed, but counted decisions exist"]
    return [
        f"{first.book}: first counted decision {first.run} ({first.commit[:10]}) is not after the v{version} freeze"
        for first in firsts
        if not _strictly_before(git, frozen, first.commit)
    ]


def _record(root: Path, version: int, definition: ProtocolDefinition = EVALUATION):
    text = (Path(root) / definition.freeze_path(version)).read_text(encoding="utf-8")
    return read_record(text, definition)


def version_of(root: Path, git, decision_commit: str) -> int | None:
    """The protocol version a decision is counted under; None when no freeze precedes it. ChangedAfterFreeze when the
    decision's commit holds that version's targets changed."""
    for version in reversed(frozen_versions(root)):
        frozen = freeze_commit(git, version)
        if frozen and _strictly_before(git, frozen, decision_commit):
            changed = changed_targets(AtCommit(git, decision_commit), _record(root, version))
            if changed:
                raise ChangedAfterFreeze(
                    f"{decision_commit[:10]} holds v{version}'s frozen {', '.join(changed)} changed: not counted"
                )
            return version
    return None


def verify(root: Path, definition: ProtocolDefinition = EVALUATION) -> list[str]:
    """Why the latest frozen version's targets differ in the working tree; empty when none differ or none is frozen."""
    versions = frozen_versions(root, definition)
    if not versions:
        return []
    changed = changed_targets(WorkingTree(root), _record(root, versions[-1], definition))
    return [f"v{versions[-1]}: {target} changed after the freeze (a change is a new version)" for target in changed]
