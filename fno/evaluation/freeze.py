"""The protocol's freeze (story S1, criteria 1 and 3). `research/evaluation/FREEZE_v<n>.md` records:
- the protocol version and the commit that last changed the protocol;
- the SHA-256 of every file and every config section the protocol's `frozen_files` item lists.

The freezer refuses unless the protocol is committed unchanged, complete, and decided item by item by the owner. It
also refuses when a listed file is missing, or when this version is already frozen, and unless the real-money gate
(story RM1) is listed and is complete and decided too, so the gate is frozen before any counted paper decision.
It then registers the protocol in the research ledger (B4). A later change to any hashed target is a new protocol
version, never an edit of a frozen one.

Everything protocol-specific comes from a `ProtocolDefinition` (story BR1a), S1's evaluation protocol by default; the
gate is required only by a definition that asks for it (BR1's breadth protocol decides no money)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from ..research_engine.ledger import Ledger, read_ledger, write_ledger
from .completeness import completeness_problems, undecided_items
from .definition import EVALUATION, ProtocolDefinition
from .gate import GATE_FILE, gate_problems
from .protocol import parse_protocol

CONFIG_PREFIX = "config.yaml:"
TARGET = re.compile(r"`([^`\s]+)`")
COMMIT_LINE = re.compile(r"^Protocol commit: `([0-9a-f]{40})`$", re.MULTILINE)
VERSION_LINE = re.compile(r"^Protocol version: ([1-9][0-9]*)$", re.MULTILINE)
HASH_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", re.MULTILINE)


class FreezeRefused(RuntimeError):
    """The protocol cannot be frozen as it stands; the message says why."""


@dataclass(frozen=True)
class FreezeRecord:
    version: int
    protocol_commit: str
    hashes: dict[str, str]  # target (a repository path, or config.yaml:<section>) -> SHA-256


def freeze_path(version: int, definition: ProtocolDefinition = EVALUATION) -> str:
    return definition.freeze_path(version)


def frozen_targets(text: str, definition: ProtocolDefinition = EVALUATION) -> list[str]:
    """The targets the `frozen_files` item lists; the protocol itself is always one."""
    item = parse_protocol(text).items.get("frozen_files")
    listed = TARGET.findall(item.value) if item else []
    return sorted({definition.protocol_file, *(t for t in listed if "/" in t or t.startswith(CONFIG_PREFIX))})


class WorkingTree:
    """Targets as the files on disk hold them."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def read(self, path: str) -> bytes | None:
        file = self.root / path
        return file.read_bytes() if file.is_file() else None


class AtCommit:
    """Targets as one commit holds them: a decision is checked against the code it was made with."""

    def __init__(self, git, commit: str):
        self.git, self.commit = git, commit

    def read(self, path: str) -> bytes | None:
        return self.git.committed_bytes(path, self.commit)


def _config_section(source, dotted: str):
    data = source.read("config.yaml")
    node = yaml.safe_load(data) if data is not None else None
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise FreezeRefused(f"config.yaml has no section {dotted!r}")
        node = node[part]
    return node


def target_hash(source, target: str) -> str:
    """A file's SHA-256, or a config section's: the SHA-256 of its canonical JSON (sorted keys, dates as text)."""
    if target.startswith(CONFIG_PREFIX):
        section = _config_section(source, target.removeprefix(CONFIG_PREFIX))
        data = json.dumps(section, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(data).hexdigest()
    data = source.read(target)
    if data is None:
        raise FreezeRefused(f"{target} is listed in frozen_files but does not exist")
    return hashlib.sha256(data).hexdigest()


def render(record: FreezeRecord, definition: ProtocolDefinition = EVALUATION) -> str:
    rows = "\n".join(f"| `{target}` | `{sha}` |" for target, sha in sorted(record.hashes.items()))
    return (
        f"# {definition.record_title}\n\nProtocol version: {record.version}\n"
        f"Protocol commit: `{record.protocol_commit}`\n\n"
        "Every target's SHA-256 at the freeze (a config section: the SHA-256 of its canonical JSON). A change to any "
        f"of them is a new protocol version with its own freeze ({definition.record_rule}).\n\n"
        f"| Target | SHA-256 |\n|---|---|\n{rows}\n"
    )


def read_record(text: str, definition: ProtocolDefinition = EVALUATION) -> FreezeRecord:
    version, commit = VERSION_LINE.search(text), COMMIT_LINE.search(text)
    hashes = dict(HASH_ROW.findall(text))
    if version is None or commit is None or definition.protocol_file not in hashes:
        raise FreezeRefused("a freeze record names its version, the protocol commit and the protocol's hash")
    return FreezeRecord(int(version.group(1)), commit.group(1), hashes)


def changed_targets(source, record: FreezeRecord) -> list[str]:
    """Targets whose bytes (or config section) in `source` differ from the freeze, or that are gone."""
    changed = []
    for target, sha in sorted(record.hashes.items()):
        try:
            if target_hash(source, target) != sha:
                changed.append(target)
        except FreezeRefused:
            changed.append(target)
    return changed


class ProtocolFreezer:
    def __init__(self, root: Path, git, ledger: Ledger | None = None, definition: ProtocolDefinition = EVALUATION):
        self.root, self.git, self.definition = Path(root), git, definition
        self.ledger = ledger or Ledger(self.root, git)

    def _checked_text(self) -> tuple[int, str]:
        text = (self.root / self.definition.protocol_file).read_text(encoding="utf-8")
        protocol = parse_protocol(text)
        problems = completeness_problems(text, protocol, self.definition.required_items)
        undecided = undecided_items(protocol)
        if problems or undecided:
            why = problems + ([f"not decided by the owner: {', '.join(undecided)}"] if undecided else [])
            raise FreezeRefused("the protocol is not ready to freeze: " + "; ".join(why))
        return protocol.version, text

    def freeze(self, today: date) -> FreezeRecord:
        version, text = self._checked_text()
        path = self.root / self.definition.freeze_path(version)
        if path.exists():
            raise FreezeRefused(f"{self.definition.freeze_path(version)} exists: a change is a new protocol version")
        targets = frozen_targets(text, self.definition)
        if self.definition.requires_gate:
            self._require_gate(targets)
        self._require_committed(targets)
        trial = self._claimed_trial(version)  # before any write: no record without its ledger id
        commit, head = self.git.commits_touching(self.definition.protocol_file)[-1], AtCommit(self.git, "HEAD")
        record = FreezeRecord(version, commit, {t: target_hash(head, t) for t in targets})
        path.write_text(render(record, self.definition), encoding="utf-8")
        self._register(trial, record, today)
        return record

    def _claimed_trial(self, version: int) -> str:
        """The lowest free id of a block claimed for this protocol's experiment (story O12e), never "highest plus
        one" and never an id of another block: none free is a refusal."""
        experiment = self.definition.ledger_experiment.format(version=version)
        try:
            return self.ledger.claims.next_free(experiment, {r["trial_id"] for r in self.ledger.rows()})
        except ValueError as none_free:
            raise FreezeRefused(str(none_free)) from none_free

    def _require_gate(self, targets: list[str]) -> None:
        """The real-money gate is frozen with the protocol, never after it (story RM1)."""
        if GATE_FILE not in targets:
            raise FreezeRefused(f"{GATE_FILE} (the real-money gate, story RM1) must be listed in frozen_files")
        data = WorkingTree(self.root).read(GATE_FILE)
        if data is None:
            raise FreezeRefused(f"{GATE_FILE} is listed in frozen_files but does not exist")
        problems = gate_problems(data.decode("utf-8"), decided=True)
        if problems:
            raise FreezeRefused("the real-money gate is not ready to freeze: " + "; ".join(problems))

    def _require_committed(self, targets: list[str]) -> None:
        """Every target committed and unchanged since HEAD: the freeze hashes what git holds, never a local edit."""
        paths = sorted({"config.yaml" if t.startswith(CONFIG_PREFIX) else t for t in targets})
        for path in paths:
            target_hash(WorkingTree(self.root), path)  # a listed file that does not exist is refused by name
            if self.git.committed_bytes(path, "HEAD") is None or not self.git.unchanged_since("HEAD", path):
                raise FreezeRefused(f"commit {path} first: the freeze hashes what git holds")

    def _register(self, trial: str, record: FreezeRecord, today: date) -> None:
        """A ledger row for the protocol (B4): prospective, no hypothesis, naming the protocol and its commit."""
        description = self.definition.ledger_description.format(version=record.version)
        experiment = self.definition.ledger_experiment.format(version=record.version)
        self.ledger.register(trial, experiment, description, "prospective", False, self.definition.protocol_file, today)
        rows = [
            r | {"protocol_commit": record.protocol_commit} if r["trial_id"] == trial else r for r in self.ledger.rows()
        ]
        self.ledger.file.write_text(write_ledger(read_ledger(write_ledger(rows))))
