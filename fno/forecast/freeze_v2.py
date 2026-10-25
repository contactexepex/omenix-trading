"""The freeze check for protocol version 2 (and later versions): G1's `freeze.py` is pinned to version 1's file names,
so this module applies the same rules to a named protocol file and freeze record. Before version 2 is frozen (no
record yet) the capture records nothing and says so; any other failure refuses loudly."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..research_engine.ledger import Git
from .freeze import COMMIT_LINE, HASH_ROW, Freeze, NotFrozen, changed_files

PROTOCOL_V2, FREEZE_V2 = "research/forecasts/PROTOCOL_v2.md", "research/forecasts/FREEZE_v2.md"


class NotYetFrozen(NotFrozen):
    """The version's freeze record does not exist yet (the expected state until the judge and orchestrator agree)."""


def read_version_freeze(text: str, protocol_file: str) -> Freeze:
    commit, hashes = COMMIT_LINE.search(text), dict(HASH_ROW.findall(text))
    if commit is None or protocol_file not in hashes:
        raise NotFrozen(f"the freeze record must name the protocol commit and the hash of {protocol_file}")
    return Freeze(commit.group(1), hashes)


def require_version_frozen(root: Path, commit: str, protocol_file: str = PROTOCOL_V2, freeze_file: str = FREEZE_V2,
                           git: Git | None = None) -> Freeze:  # fmt: skip
    git, root = git or Git(Path(root)), Path(root)
    if not (root / freeze_file).is_file():
        raise NotYetFrozen(f"{freeze_file} does not exist: {protocol_file} is not frozen yet")
    freeze = read_version_freeze((root / freeze_file).read_text(encoding="utf-8"), protocol_file)
    recorded = git.first_commit_containing(freeze.protocol_commit, freeze_file)
    if not git.is_ancestor(freeze.protocol_commit, commit) or not recorded or not git.is_ancestor(recorded, commit):
        raise NotFrozen(f"the {protocol_file} freeze is not in the history of {commit[:10]}")
    text = git.committed_text(protocol_file, freeze.protocol_commit)
    if text is None or hashlib.sha256(text.encode("utf-8")).hexdigest() != freeze.hashes[protocol_file]:
        raise NotFrozen(f"{protocol_file} at the protocol commit is not the frozen version")
    changed = changed_files(root, freeze)
    if changed:
        raise NotFrozen(f"frozen files changed after the freeze: {', '.join(changed)} (a change needs a new version)")
    return freeze
