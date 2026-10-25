"""Book 2's trade envelopes as files (story D4): `playbook/envelopes/<name>-v<n>.yaml`, one per playbook version Book 2
may trade. They sit in a subfolder because D1's loader reads every `*.yaml` directly in `playbook/` as a strategy. Each
file names its version and the status of each action; an unknown action, an unknown status or a file whose name and
version disagree is refused. The SHA-256 of the file's bytes is its D6 component `trade_envelope:<name>-v<n>`."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

import yaml

from ..constants import PLAYBOOK_FOLDER
from .envelope import ActionStatus, EnvelopeAction, TradeEnvelope, VersionKey

ENVELOPE_FOLDER = "envelopes"
COMPONENT_PREFIX = "trade_envelope:"  # "trade" keeps it apart from Hybrid's forecast envelope (fno/ai/envelope.py)


class EnvelopeError(ValueError):
    pass


def component_key(version: VersionKey) -> str:
    return f"{COMPONENT_PREFIX}{version[0]}-v{version[1]}"


def parse_envelope(raw: bytes, where: str) -> TradeEnvelope:
    data = yaml.safe_load(raw.decode("utf-8")) or {}
    if set(data) != {"playbook", "version", "actions"} or not isinstance(data["actions"], dict):
        raise EnvelopeError(f"{where}: needs exactly playbook, version and actions")
    statuses = {}
    for action, status in data["actions"].items():
        if action not in set(EnvelopeAction) or status not in set(ActionStatus):
            raise EnvelopeError(f"{where}: unknown action or status {action!r}: {status!r}")
        statuses[EnvelopeAction(action)] = ActionStatus(status)
    key = (str(data["playbook"]), int(data["version"]))
    return TradeEnvelope(key, statuses, hashlib.sha256(raw).hexdigest())


class TradeEnvelopes(ABC):
    @abstractmethod
    def all(self) -> dict[VersionKey, TradeEnvelope]:
        """Every trade envelope, by version; EnvelopeError on a damaged file."""


class EnvelopeFiles(TradeEnvelopes):
    def __init__(self, root: Path):
        self.folder = Path(root) / PLAYBOOK_FOLDER / ENVELOPE_FOLDER

    def all(self) -> dict[VersionKey, TradeEnvelope]:
        found = {}
        for path in sorted(self.folder.glob("*.yaml")) if self.folder.is_dir() else ():
            envelope = parse_envelope(path.read_bytes(), str(path))
            if path.name != f"{envelope.version[0]}-v{envelope.version[1]}.yaml":
                raise EnvelopeError(f"{path}: the file name must match its playbook and version")
            found[envelope.version] = envelope
        return found


def served_envelopes(envelopes: dict[VersionKey, TradeEnvelope], versions) -> dict[str, str]:
    """The `served` entries a Book 2 decision records for the versions it could trade: the same keys and hashes as the
    D6 components, so D6 unscores a decision made on any other envelope."""
    return {component_key(v): envelopes[v].sha256 for v in versions if v in envelopes}
