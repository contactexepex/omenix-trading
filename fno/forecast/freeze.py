"""The forecast protocol's freeze (story G1 criterion 3): `research/forecasts/FREEZE.md` names the protocol commit and
the SHA-256 of every frozen file. Story G4 calls `require_frozen_before` before scoring: the freeze must be in the
history of the commit that holds the first scored forecast, and every frozen file must still have its frozen bytes.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..research_engine.ledger import Git

FREEZE_FILE = "research/forecasts/FREEZE.md"
PROTOCOL_FILE = "research/forecasts/PROTOCOL.md"
COMMIT_LINE = re.compile(r"^Protocol commit: `([0-9a-f]{40})`$", re.MULTILINE)
HASH_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", re.MULTILINE)


class NotFrozen(RuntimeError):
    """The protocol is not frozen, or not frozen before the commit asked about, or a frozen file changed."""


@dataclass(frozen=True)
class Freeze:
    protocol_commit: str
    hashes: dict[str, str]  # repository path -> SHA-256 at the freeze


def read_freeze(text: str) -> Freeze:
    commit = COMMIT_LINE.search(text)
    hashes = dict(HASH_ROW.findall(text))
    if commit is None or PROTOCOL_FILE not in hashes:
        raise NotFrozen(f"{FREEZE_FILE} must name the protocol commit and the hash of {PROTOCOL_FILE}")
    return Freeze(commit.group(1), hashes)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_files(root: Path, freeze: Freeze) -> list[str]:
    """Frozen files whose bytes differ from the freeze (or that are gone)."""
    return [p for p, h in freeze.hashes.items() if not (root / p).is_file() or file_sha256(root / p) != h]


def require_frozen_before(root: Path, commit: str, git: Git | None = None) -> Freeze:
    """The freeze, if the protocol commit and the freeze record are both in the history of `commit` and no frozen
    file changed; NotFrozen with the reason otherwise."""
    git = git or Git(Path(root))
    path = Path(root) / FREEZE_FILE
    if not path.is_file():
        raise NotFrozen(f"{FREEZE_FILE} does not exist: the protocol is not frozen")
    freeze = read_freeze(path.read_text(encoding="utf-8"))
    recorded = git.first_commit_containing(freeze.protocol_commit, FREEZE_FILE)
    if not git.is_ancestor(freeze.protocol_commit, commit) or not recorded or not git.is_ancestor(recorded, commit):
        raise NotFrozen(f"the freeze is not in the history of {commit[:10]}")
    at_commit = git.committed_text(PROTOCOL_FILE, freeze.protocol_commit)
    if at_commit is None or hashlib.sha256(at_commit.encode("utf-8")).hexdigest() != freeze.hashes[PROTOCOL_FILE]:
        raise NotFrozen(f"{PROTOCOL_FILE} at the protocol commit is not the frozen version")
    changed = changed_files(Path(root), freeze)
    if changed:
        raise NotFrozen(f"frozen files changed after the freeze: {', '.join(changed)} (a change needs a new version)")
    return freeze
